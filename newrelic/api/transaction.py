import os
import sys
import time
import weakref
import threading
import traceback
import logging
import warnings
import itertools
import random

try:
    import thread
except ImportError:
    import _thread as thread

from collections import deque

import newrelic.packages.six as six

import newrelic.core.transaction_node
import newrelic.core.database_node
import newrelic.core.error_node

import newrelic.api.time_trace

from newrelic.core.stats_engine import CustomMetrics
from newrelic.core.transaction_cache import transaction_cache
from newrelic.core.thread_utilization import utilization_tracker

_logger = logging.getLogger(__name__)

class Transaction(object):

    STATE_PENDING = 0
    STATE_RUNNING = 1
    STATE_STOPPED = 2

    def __init__(self, application, enabled=None):

        self._application = application

        self.thread_id = transaction_cache().current_thread_id()

        self._transaction_id = id(self)
        self._transaction_lock = threading.Lock()

        self._dead = False

        self._state = self.STATE_PENDING
        self._settings = None

        self._priority = 0
        self._group = None
        self._name = None

        self._frameworks = set()

        self._frozen_path = None

        self._node_stack = []

        self._request_uri = None

        self.queue_start = 0.0

        self.start_time = 0.0
        self.end_time = 0.0

        self.stopped = False

        self._trace_node_count = 0

        self._errors = []
        self._slow_sql = []

        self._stack_trace_count = 0
        self._explain_plan_count = 0

        self._string_cache = {}

        self._custom_params = {}
        self._request_params = {}

        self._utilization_tracker = None

        self._thread_utilization_start = None
        self._thread_utilization_end = None
        self._thread_utilization_value = None

        self._cpu_user_time_start = None
        self._cpu_user_time_end = None
        self._cpu_user_time_value = 0.0

        self._read_length = None

        self._read_start = None
        self._read_end = None

        self._sent_start = None
        self._sent_end = None

        self._bytes_read = 0
        self._bytes_sent = 0

        self._calls_read = 0
        self._calls_readline = 0
        self._calls_readlines = 0

        self._calls_write = 0
        self._calls_yield = 0

        self._request_environment = {}
        self._response_properties = {}
        self._transaction_metrics = {}

        self.background_task = False

        self.enabled = False
        self.autorum_disabled = False

        self.ignore_transaction = False
        self.suppress_apdex = False
        self.suppress_transaction_trace = False

        self.capture_params = False
        self.ignored_params = []

        self.response_code = 0

        self.apdex = 0

        self.rum_token = None
        self.rum_trace = False

        # 16-digit random hex. Padded with zeros in the front.
        self.guid = '%016x' % random.getrandbits(64)

        self.client_cross_process_id = None
        self.client_account_id = None
        self.client_application_id = None
        self.referring_transaction_guid = None
        self.record_tt = False

        self._custom_metrics = CustomMetrics()

        self._profile_samples = deque()
        self._profile_frames = {}
        self._profile_skip = 1
        self._profile_count = 0

        global_settings = application.global_settings

        if global_settings.enabled:
            if enabled or (enabled is None and application.enabled):
                self._settings = application.settings
                if not self._settings:
                    application.activate()

                    # We see again if the settings is now valid
                    # in case startup timeout had been specified
                    # and registration had been started and
                    # completed within the timeout.

                    self._settings = application.settings

                if self._settings:
                    self.enabled = True

    def __del__(self):
        self._dead = True
        if self._state == self.STATE_RUNNING:
            self.__exit__(None, None, None)

    def save_transaction(self):
        transaction_cache().save_transaction(self)

    def drop_transaction(self):
        transaction_cache().drop_transaction(self)

    def __enter__(self):

        assert(self._state == self.STATE_PENDING)

        # Bail out if the transaction is not enabled.

        if not self.enabled:
            return self

        # Mark transaction as active and update state
        # used to validate correct usage of class.

        self._state = self.STATE_RUNNING

        # Cache transaction in thread/coroutine local
        # storage so that it can be accessed from
        # anywhere in the context of the transaction.

        try:
            self.save_transaction()
        except:  # Catch all
            self._state = self.STATE_PENDING
            self.enabled = False
            raise

        # Record the start time for transaction.

        self.start_time = time.time()

        # Record initial CPU user time.

        self._cpu_user_time_start = os.times()[0]

        # Calculate initial thread utilisation factor.
        # For now we only do this if we know it is an
        # actual thread and not a greenlet.

        if (not hasattr(sys, '_current_frames') or
                self.thread_id in sys._current_frames()):
            thread_instance = threading.currentThread()
            self._utilization_tracker = utilization_tracker(
                    self.application.name)
            if self._utilization_tracker:
                self._utilization_tracker.enter_transaction(thread_instance)
                self._thread_utilization_start = \
                        self._utilization_tracker.utilization_count()

        # We need to push an object onto the top of the
        # node stack so that children can reach back and
        # add themselves as children to the parent. We
        # can't use ourself though as we then end up
        # with a reference count cycle which will cause
        # the destructor to never be called if the
        # __exit__() function is never called. We
        # instead push on to the top of the node stack a
        # dummy time trace object and when done we will
        # just grab what we need from that.

        self._node_stack.append(newrelic.api.time_trace.TimeTrace(None))

        return self

    def __exit__(self, exc, value, tb):

        # Bail out if the transaction is not enabled.

        if not self.enabled:
            return

        # Mark as stopped and drop the transaction from
        # thread/coroutine local storage.
        #
        # Note that we validate the saved transaction ID
        # against that for the current transaction object
        # to protect against situations where a copy was
        # made of the transaction object for some reason.
        # Such a copy when garbage collected could trigger
        # this function and cause a deadlock if it occurs
        # while original transaction was being recorded.

        self._state = self.STATE_STOPPED

        if self._transaction_id != id(self):
            return

        if not self._settings:
            return

        if not self._dead:
            try:
                self.drop_transaction()
            except:  # Catch all
                _logger.exception('Unable to drop transaction.')
                raise

        # Record error if one was registered.

        if exc is not None and value is not None and tb is not None:
            self.record_exception(exc, value, tb)

        # Record the end time for transaction and then
        # calculate the duration.

        if not self.stopped:
            self.end_time = time.time()

        duration = self.end_time - self.start_time

        # Calculate overall user time.

        if not self._cpu_user_time_end:
            self._cpu_user_time_end = os.times()[0]

        if duration and self._cpu_user_time_end:
            self._cpu_user_time_value = (self._cpu_user_time_end -
                    self._cpu_user_time_start)

        # Calculate thread utilisation factor. Note that even if
        # we are tracking thread utilization we skip calculation
        # if duration is zero. Under normal circumstances this
        # should not occur but may if the system clock is wound
        # backwards and duration was squashed to zero due to the
        # request appearing to finish before it started. It may
        # also occur if true response time came in under the
        # resolution of the clock being used, but that is highly
        # unlikely as the overhead of the agent itself should
        # always ensure that that is hard to achieve.

        if self._utilization_tracker:
            self._utilization_tracker.exit_transaction()
            if self._thread_utilization_start and duration > 0.0:
                if not self._thread_utilization_end:
                    self._thread_utilization_end = (
                            self._utilization_tracker.utilization_count())
                self._thread_utilization_value = (
                        self._thread_utilization_end -
                        self._thread_utilization_start) / duration

        # Derive generated values from the raw data. The
        # dummy root node has exclusive time of children
        # as negative number. Add our own duration to get
        # our own exclusive time.

        root = self._node_stack.pop()
        children = root.children

        exclusive = duration + root.exclusive

        # Construct final root node of transaction trace.
        # Freeze path in case not already done. This will
        # construct out path.

        self._freeze_path()

        if self.background_task:
            transaction_type = 'OtherTransaction'
        else:
            transaction_type = 'WebTransaction'

        group = self._group

        if group is None:
            if self.background_task:
                group = 'Python'
            else:
                group = 'Uri'

        if self.response_code != 0:
            self._response_properties['STATUS'] = str(self.response_code)

        metrics = self._transaction_metrics

        if self._bytes_read != 0:
            metrics['WSGI/Input/Bytes'] = self._bytes_read
        if self._bytes_sent != 0:
            metrics['WSGI/Output/Bytes'] = self._bytes_sent
        if self._calls_read != 0:
            metrics['WSGI/Input/Calls/read'] = self._calls_read
        if self._calls_readline != 0:
            metrics['WSGI/Input/Calls/readline'] = self._calls_readline
        if self._calls_readlines != 0:
            metrics['WSGI/Input/Calls/readlines'] = self._calls_readlines
        if self._calls_write != 0:
            metrics['WSGI/Output/Calls/write'] = self._calls_write
        if self._calls_yield != 0:
            metrics['WSGI/Output/Calls/yield'] = self._calls_yield

        if self._thread_utilization_value:
            metrics['Thread/Concurrency'] = \
                    '%.4f' % self._thread_utilization_value

        read_duration = 0
        if self._read_start:
            read_duration = self._read_end - self._read_start
            metrics['WSGI/Input/Time'] = '%.4f' % read_duration
        self.record_custom_metric('Python/WSGI/Input/Time', read_duration)

        sent_duration = 0
        if self._sent_start:
            if not self._sent_end:
                self._sent_end = time.time()
            sent_duration = self._sent_end - self._sent_start
            metrics['WSGI/Output/Time'] = '%.4f' % sent_duration
        self.record_custom_metric('Python/WSGI/Output/Time',
                           sent_duration)

        if self.queue_start:
            queue_wait = self.start_time - self.queue_start
            if queue_wait < 0:
                queue_wait = 0
            metrics['WebFrontend/QueueTime'] = '%.4f' % queue_wait

        self.record_custom_metric('Python/WSGI/Input/Bytes',
                           self._bytes_read)

        self.record_custom_metric('Python/WSGI/Input/Calls/read',
                           self._calls_read)
        self.record_custom_metric('Python/WSGI/Input/Calls/readline',
                           self._calls_readline)
        self.record_custom_metric('Python/WSGI/Input/Calls/readlines',
                           self._calls_readlines)

        self.record_custom_metric('Python/WSGI/Output/Bytes',
                           self._bytes_sent)
        self.record_custom_metric('Python/WSGI/Output/Calls/yield',
                           self._calls_yield)
        self.record_custom_metric('Python/WSGI/Output/Calls/write',
                           self._calls_write)

        if self._frameworks:
            for framework, version in self._frameworks:
                self.record_custom_metric('Python/Framework/%s/%s' %
                    (framework, version), 1)

        request_params = {}
        parameter_groups = {}

        if self.capture_params:
            request_params = self._request_params

        if self._request_environment:
            parameter_groups['Request environment'] = self._request_environment
        if self._response_properties:
            parameter_groups['Response properties'] = self._response_properties

        if self._transaction_metrics:
            parameter_groups['Transaction metrics'] = self._transaction_metrics

        node = newrelic.core.transaction_node.TransactionNode(
                settings=self._settings,
                path=self.path,
                type=transaction_type,
                group=group,
                name=self._name,
                request_uri=self._request_uri,
                response_code=self.response_code,
                request_params=request_params,
                custom_params=self._custom_params,
                queue_start=self.queue_start,
                start_time=self.start_time,
                end_time=self.end_time,
                duration=duration,
                exclusive=exclusive,
                children=tuple(children),
                errors=tuple(self._errors),
                slow_sql=tuple(self._slow_sql),
                apdex_t=self.apdex,
                suppress_apdex=self.suppress_apdex,
                custom_metrics=self._custom_metrics,
                parameter_groups=parameter_groups,
                guid=self.guid,
                rum_trace = self.rum_trace,
                cpu_time=self._cpu_user_time_value,
                suppress_transaction_trace=self.suppress_transaction_trace,
                client_cross_process_id=self.client_cross_process_id,
                referring_transaction_guid=self.referring_transaction_guid,
                record_tt = self.record_tt,
                )

        # Clear settings as we are all done and don't need it
        # anymore.

        self._settings = None
        self.enabled = False

        # Unless we are ignoring the transaction, record it. We
        # need to lock the profile samples and replace it with
        # an empty list just in case the thread profiler kicks
        # in just as we are trying to record the transaction.
        # If we don't, when processing the samples, addition of
        # new samples can cause an error.

        if not self.ignore_transaction:
            profile_samples = []

            if self._profile_samples:
                with self._transaction_lock:
                    profile_samples = self._profile_samples
                    self._profile_samples = deque()

            self._application.record_transaction(node,
                    (self.background_task, profile_samples))

    @property
    def state(self):
        return self._state

    @property
    def settings(self):
        return self._settings

    @property
    def application(self):
        return self._application

    @property
    def name(self):
        return self._name

    @property
    def group(self):
        return self._group

    @property
    def path(self):
        if self._frozen_path:
            return self._frozen_path

        if self.background_task:
            transaction_type = 'OtherTransaction'
        else:
            transaction_type = 'WebTransaction'

        group = self._group

        if group is None:
            if self.background_task:
                group = 'Python'
            else:
                group = 'Uri'

        name = self._name

        if name is None:
            name = '<undefined>'

        # Stripping the leading slash on the request URL held by
        # name when type is 'Uri' is to keep compatibility with
        # PHP agent and also possibly other agents. Leading
        # slash it not deleted for other category groups as the
        # leading slash may be significant in that situation.

        if self._group in ['Uri', 'NormalizedUri'] and name[:1] == '/':
            path = '%s/%s%s' % (transaction_type, group, name)
        else:
            path = '%s/%s/%s' % (transaction_type, group, name)

        return path

    @property
    def profile_sample(self):
        return self._profile_samples

    def add_profile_sample(self, stack_trace):
        if self._state != self.STATE_RUNNING:
            return

        self._profile_count += 1

        if self._profile_count < self._profile_skip:
            return

        self._profile_count = 0

        with self._transaction_lock:
            new_stack_trace = tuple(self._profile_frames.setdefault(
                    frame, frame) for frame in stack_trace)
            self._profile_samples.append(new_stack_trace)

            agent_limits = self._application.global_settings.agent_limits
            profile_maximum = agent_limits.xray_profile_maximum

            if len(self._profile_samples) >= profile_maximum:
                self._profile_samples = deque(itertools.islice(
                        self._profile_samples, 0,
                        len(self._profile_samples), 2))
                self._profile_skip = 2 * self._profile_skip

    def _freeze_path(self):
        if self._frozen_path is None:
            self._priority = None

            if self._group == 'Uri' and self._name != '/':
                # Apply URL normalization rules. We would only have raw
                # URLs where we were not specifically naming the web
                # transactions for a specific web framework to be a code
                # handler or otherwise.

                name, ignore = self._application.normalize_name(
                        self._name, 'url')

                if self._name != name:
                    self._group = 'NormalizedUri'
                    self._name = name

                self.ignore_transaction = self.ignore_transaction or ignore

            # Apply transaction rules on the full transaction name.
            # The path is frozen at this point and cannot be further
            # changed.

            self._frozen_path, ignore = self._application.normalize_name(
                    self.path, 'transaction')

            self.ignore_transaction = self.ignore_transaction or ignore

            # Look up the apdex from the table of key transactions. If
            # current transaction is not a key transaction then use the
            # default apdex from settings. The path used at this point
            # is the frozen path.

            self.apdex = (self._settings.web_transactions_apdex.get(
                self.path) or self._settings.apdex_t)

    def set_transaction_name(self, name, group=None, priority=None):

        # Always perform this operation even if the transaction
        # is not active at the time as will be called from
        # constructor. If path has been frozen do not allow
        # name/group to be overridden. New priority then must be
        # same or greater than existing priority. If no priority
        # always override the existing name/group if not frozen.

        if self._priority is None:
            return

        if priority is not None and priority < self._priority:
            return

        if priority is not None:
            self._priority = priority

        # The name can be a URL for the default case. URLs are
        # supposed to be ASCII but can get a URL with illegal
        # non ASCII characters. As the rule patterns and
        # replacements are Unicode then can get Unicode
        # conversion warnings or errors when URL is converted to
        # Unicode and default encoding is ASCII. Thus need to
        # convert URL to Unicode as Latin-1 explicitly to avoid
        # problems with illegal characters.

        if isinstance(name, bytes):
            name = name.decode('Latin-1')

        # Deal with users who use group wrongly and add a leading
        # slash on it. This will cause an empty segment which we
        # want to avoid. In that case insert back in Function as
        # the leading segment.

        group = group or 'Function'

        if group.startswith('/'):
            group = 'Function' + group

        self._group = group
        self._name = name

    def name_transaction(self, name, group=None, priority=None):
        #warnings.warn('Internal API change. Use set_transaction_name() '
        #        'instead of name_transaction().', DeprecationWarning,
        #        stacklevel=2)

        return self.set_transaction_name(name, group, priority)

    def record_exception(self, exc=None, value=None, tb=None,
                         params={}, ignore_errors=[]):

        # Bail out if the transaction is not active or
        # collection of errors not enabled.

        if not self._settings:
            return

        settings = self._settings
        error_collector = settings.error_collector

        if not error_collector.enabled or not settings.collect_errors:
            return

        # If no exception details provided, use current exception.

        if exc is None and value is None and tb is None:
            exc, value, tb = sys.exc_info()

        # Has to be an error to be logged.

        if exc is None or value is None or tb is None:
            return

        # Where ignore_errors is a callable it should return a
        # tri-state variable with the following behavior.
        #
        #   True - Ignore the error.
        #   False- Record the error.
        #   None - Use the default ignore rules.

        should_ignore = None

        if callable(ignore_errors):
            should_ignore = ignore_errors(exc, value, tb)
            if should_ignore:
                return

        module = value.__class__.__module__
        name = value.__class__.__name__

        if should_ignore is None:
            # We need to check for module.name and module:name.
            # Originally we used module.class but that was
            # inconsistent with everything else which used
            # module:name. So changed to use ':' as separator, but
            # for backward compatability need to support '.' as
            # separator for time being. Check that with the ':'
            # last as we will use that name as the exception type.

            if module:
                fullname = '%s.%s' % (module, name)
            else:
                fullname = name

            if not callable(ignore_errors) and fullname in ignore_errors:
                return

            if fullname in error_collector.ignore_errors:
                return

            if module:
                fullname = '%s:%s' % (module, name)
            else:
                fullname = name

            if not callable(ignore_errors) and fullname in ignore_errors:
                return

            if fullname in error_collector.ignore_errors:
                return

        else:
            if module:
                fullname = '%s:%s' % (module, name)
            else:
                fullname = name

        # Only remember up to limit of what can be caught for a
        # single transaction. This could be trimmed further
        # later if there are already recorded errors and would
        # go over the harvest limit.

        if len(self._errors) >= settings.agent_limits.errors_per_transaction:
            return

        # Only add params if High Security Mode is off.

        if settings.high_security:
            custom_params = {}

        else:
            if params:
                custom_params = dict(self._custom_params)
                custom_params.update(params)
            else:
                custom_params = self._custom_params

        exc_type = exc.__name__

        try:
            message = str(value)
        except Exception:
            try:
                # Assume JSON encoding can handle unicode.
                message = six.text_type(value)
            except Exception:
                message = '<unprintable %s object>' % type(value).__name__

        # Check that we have not recorded this exception
        # previously for this transaction due to multiple
        # error traces triggering. This is not going to be
        # exact but the UI hides exceptions of same type
        # anyway. Better that we under count exceptions of
        # same type and message rather than count same one
        # multiple times.

        for error in self._errors:
            if error.type == fullname and error.message == message:
                return

        stack_trace = traceback.format_exception(exc, value, tb)

        node = newrelic.core.error_node.ErrorNode(
                timestamp=time.time(),
                type=fullname,
                message=message,
                stack_trace=stack_trace,
                custom_params=custom_params,
                file_name=None,
                line_number=None,
                source=None)

        # TODO Errors are recorded in time order. If
        # there are two exceptions of same type and
        # different message, the UI displays the first
        # one. In the PHP agent it was recording the
        # errors in reverse time order and so the UI
        # displayed the last one. What is the the
        # official order in which they should be sent.

        self._errors.append(node)

    def notice_error(self, exc, value, tb, params={}, ignore_errors=[]):
        warnings.warn('Internal API change. Use record_exception() '
                'instead of notice_error().', DeprecationWarning,
                stacklevel=2)

        self.record_exception(exc, value, tb, params, ignore_errors)

    def record_custom_metric(self, name, value):
        self._custom_metrics.record_custom_metric(name, value)

    def record_custom_metrics(self, metrics):
        for name, value in metrics:
            self._custom_metrics.record_custom_metric(name, value)

    def record_metric(self, name, value):
        warnings.warn('Internal API change. Use record_custom_metric() '
                'instead of record_metric().', DeprecationWarning,
                stacklevel=2)

        return self.record_custom_metric(name, value)

    def active_node(self):
        if self._node_stack:
            return self._node_stack[-1]

    def _intern_string(self, value):
        return self._string_cache.setdefault(value, value)

    def _push_current(self, node):
        self._node_stack.append(node)

    def _pop_current(self, node):
        last = self._node_stack.pop()
        assert last == node
        parent = self._node_stack[-1]
        return parent

    def _process_node(self, node):
        self._trace_node_count += 1
        node.node_count = self._trace_node_count

        if type(node) is newrelic.core.database_node.DatabaseNode:
            settings = self._settings
            if not settings.collect_traces:
                return
            if (not settings.slow_sql.enabled and
                    not settings.transaction_tracer.explain_enabled):
                return
            if settings.transaction_tracer.record_sql == 'off':
                return
            if node.duration < settings.transaction_tracer.explain_threshold:
                return
            self._slow_sql.append(node)

    def stop_recording(self):
        if not self.enabled:
            return

        if self.stopped:
            return

        if self.end_time:
            return

        self.end_time = time.time()
        self.stopped = True

        if self._utilization_tracker:
            if self._thread_utilization_start:
                if not self._thread_utilization_end:
                    self._thread_utilization_end = (
                            self._utilization_tracker.utilization_count())

        self._cpu_user_time_end = os.times()[0]

    def add_custom_parameter(self, name, value):
        if not self._settings: 
            return 

        if not self._settings.high_security:
            self._custom_params[name] = value

    def add_custom_parameters(self, items):
        for name, value in items:
            self._custom_params[name] = value

    def add_user_attribute(self, name, value):
        #warnings.warn('Internal API change. Use add_custom_parameter() '
        #        'instead of add_user_attribute().', DeprecationWarning,
        #        stacklevel=2)
        self.add_custom_parameter(name, value)

    def add_user_attributes(self, items):
        #warnings.warn('Internal API change. Use add_custom_parameters() '
        #        'instead of add_user_attributes().', DeprecationWarning,
        #        stacklevel=2)
        self.add_custom_parameters(items)

    def dump(self, file):
        """Dumps details about the transaction to the file object."""

        print >> file, 'Application: %s' % (
                self.application.name)
        print >> file, 'Time Started: %s' % (
                time.asctime(time.localtime(self.start_time)))
        print >> file, 'Thread Id: %r' % (
                self.thread_id,)
        print >> file, 'Current Status: %d' % (
                self._state)
        print >> file, 'Recording Enabled: %s' % (
                self.enabled)
        print >> file, 'Ignore Transaction: %s' % (
                self.ignore_transaction)
        print >> file, 'Transaction Dead: %s' % (
                self._dead)
        print >> file, 'Transaction Stopped: %s' % (
                self.stopped)
        print >> file, 'Background Task: %s' % (
                self.background_task)
        print >> file, 'Request URI: %s' % (
                self._request_uri)
        print >> file, 'Transaction Group: %s' % (
                self._group)
        print >> file, 'Transaction Name: %s' % (
                self._name)
        print >> file, 'Name Priority: %r' % (
                self._priority)
        print >> file, 'Frozen Path: %s' % (
                self._frozen_path)
        print >> file, 'AutoRUM Disabled: %s' % (
                self.autorum_disabled)
        print >> file, 'Supress Apdex: %s' % (
                self.suppress_apdex)

        print >> file, 'Node Stack:'
        for node in self._node_stack[1:]:
            node.dump(file)


def current_transaction():
    current = transaction_cache().current_transaction()
    if current and (current.ignore_transaction or current.stopped):
        return None
    return current

def transaction():
    warnings.warn('Internal API change. Use current_transaction() '
            'instead of transaction().', DeprecationWarning, stacklevel=2)

    return current_transaction()
