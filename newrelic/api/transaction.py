from __future__ import with_statement

import os
import sys
import time
import weakref
import thread
import threading
import traceback
import logging
import warnings

import newrelic.core.config

import newrelic.core.transaction_node
import newrelic.core.database_node
import newrelic.core.error_node
import newrelic.core.samplers

import newrelic.api.time_trace

from newrelic.core.stats_engine import ValueMetrics
from newrelic.core.metric import ValueMetric

_logger = logging.getLogger(__name__)

STATE_PENDING = 0
STATE_RUNNING = 1
STATE_STOPPED = 2

CONCURRENCY_THREADING = 0
CONCURRENCY_COROUTINE = 1

class Transaction(object):

    _transactions = weakref.WeakValueDictionary()

    @classmethod
    def _current_thread_id(cls):
        """Returns the thread ID for the caller.

        When greenlets are present and we detect we are running in the
        greenlet then we use the greenlet ID instead of the thread ID.

        """

        greenlet = sys.modules.get('greenlet')

        if greenlet:
            # Greenlet objects are maintained in a tree structure with
            # the 'parent' attribute pointing to that which a specific
            # instance is associated with. Only the root node has no
            # parent. This node is special and is the one which
            # corresponds to the original thread where the greenlet
            # module was imported and initialised. That root greenlet is
            # never actually running and we should always ignore it. In
            # all other cases where we can obtain a current greenlet,
            # then it should indicate we are running as a greenlet.

            current = greenlet.getcurrent()
            if current is not None and current.parent:
                return id(current)

        return thread.get_ident()

    @classmethod
    def _current_transaction(cls):
        """Return the transaction object if one exists for the currently
        executing thread.

        """

        return cls._transactions.get(cls._current_thread_id())

    @classmethod
    def _lookup_transaction(cls, thread_id):
        """Returns the transaction object if one exists for the thread
        with the corresponding thread ID.

        Note that if a thread is actually running as a greenlet, using
        the thread ID from the set of current frames returned by the
        sys._current_frames() will not actually match. That is because
        that thread ID is that of the real Python thread in which the
        greenlets are running.

        """

        return cls._transactions.get(thread_id)

    @classmethod
    def _active_threads(cls):
        """Returns an iterator over all current stack frames for all
        active threads in the process. The result for each is a tuple
        consisting of the thread identifier, a categorisation of the
        type of thread, and the stack frame. Note that we actually treat
        any greenlets as threads as well. In that case the thread ID is
        the id() of the greenlet.

        This is in this class for convenience as needs to access the
        currently active transactions to categorise transaction threads
        as being for web transactions or background tasks.

        """

        # First yield up those for real Python threads.

        for thread_id, frame in sys._current_frames().items():
            transaction = cls._transactions.get(thread_id)
            if transaction is not None:
                if transaction.background_task:
                    yield thread_id, 'BACKGROUND', frame
                else:
                    yield thread_id, 'REQUEST', frame
            else:
                # Note that there may not always be a thread object.
                # This is because thread could have been created direct
                # against the thread module rather than via the high
                # level threading module. Categorise anything we can't
                # obtain a name for as being 'OTHER'.

                thread = threading._active.get(thread_id)
                if thread is not None and thread.getName().startswith('NR-'):
                    yield thread_id, 'AGENT', frame
                else:
                    yield thread_id, 'OTHER', frame

        # Now yield up those corresponding to greenlets. Right now only
        # doing this for greenlets in which any active transactions are
        # running. We don't have a way of knowing what non transaction
        # threads are running.

        for thread_id, transaction in cls._transactions.items():
            if transaction._greenlet is not None:
                gr = transaction._greenlet()
                if gr and gr.gr_frame is not None:
                    if transaction.background_task:
                        yield thread_id, 'BACKGROUND', gr.gr_frame
                    else:
                        yield thread_id, 'REQUEST', gr.gr_frame

    @classmethod
    def _save_transaction(cls, transaction):
        """Saves the specified transaction away under the thread ID of
        the current executing thread. Will also cache the thread ID and
        the type of concurrency mechanism being used in the transaction.

        """

        thread_id = cls._current_thread_id()

        if thread_id in cls._transactions:
            raise RuntimeError('transaction already active')

        cls._transactions[thread_id] = transaction

        transaction._thread_id = thread_id
        transaction._concurrency_model = CONCURRENCY_THREADING

        # We judge whether we are actually running in a coroutine by
        # seeing if the current thread ID is actually listed in the set
        # of all current frames for executing threads. If we are
        # executing within a greenlet, then thread.get_ident() will
        # return the greenlet identifier. This will not be a key in
        # dictionary of all current frames because that will still be
        # the original standard thread which all greenlets are running
        # within.

        if hasattr(sys, '_current_frames'):
            if thread_id not in sys._current_frames():
                transaction._concurrency_model = CONCURRENCY_COROUTINE
                greenlet = sys.modules.get('greenlet')
                if greenlet:
                    transaction._greenlet = weakref.ref(greenlet.getcurrent())

    @classmethod
    def _drop_transaction(cls, transaction):
        """Drops the specified transaction, validating that it is
        actually saved away under the current executing thread.

        """

        thread_id = transaction._thread_id

        if not thread_id in cls._transactions:
            raise RuntimeError('no active transaction')

        current = cls._transactions.get(thread_id)

        if transaction != current:
            raise RuntimeError('not the current transaction')

        transaction._thread_id = None
        transaction._concurrency_model = None
        transaction._greenlet = None

        del cls._transactions[thread_id]

    def __init__(self, application, enabled=None):

        self._application = application

        self._thread_id = None
        self._concurrency_model = None
        self._greenlet = None

        self._dead = False

        self._state = STATE_PENDING
        self._settings = None

        self._priority = 0
        self._group = None
        self._name = None

        self._frozen_path = None

        self._node_stack = []

        self._request_uri = None

        self.queue_start = 0.0

        self.start_time = 0.0
        self.end_time = 0.0

        self.stopped = False

        self._errors = []
        self._slow_sql = []

        self._stack_trace_count = 0
        self._explain_plan_count = 0

        self._string_cache = {}

        self._custom_params = {}
        self._user_attrs = {}
        self._request_params = {}

        self._thread_utilization = None

        self._thread_utilization_start = None
        self._thread_utilization_end = None
        self._thread_utilization_value = None

        self._cpu_user_time_start = None
        self._cpu_user_time_end = None
        self._cpu_user_time_value = None
        self._cpu_utilization_value = None

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
        self.rum_guid = None

        self._custom_metrics = ValueMetrics()

        global_settings = newrelic.core.config.global_settings()

        if global_settings.enabled:
            if enabled or (enabled is None and application.enabled):
                self._settings = self._application.settings
                if not self._settings:
                    self._application.activate()

                    # We see again if the settings is now valid
                    # in case startup timeout had been specified
                    # and registration had been started and
                    # completed within the timeout.

                    self._settings = self._application.settings

                if self._settings:
                    self.enabled = True

    def __del__(self):
        self._dead = True
        if self._state == STATE_RUNNING:
            self.__exit__(None, None, None)

    def __enter__(self):

        assert(self._state == STATE_PENDING)

        # Bail out if the transaction is not enabled.

        if not self.enabled:
            return self

        # Mark transaction as active and update state
        # used to validate correct usage of class.

        self._state = STATE_RUNNING

        # Cache transaction in thread/coroutine local
        # storage so that it can be accessed from
        # anywhere in the context of the transaction.

        try:
            self._save_transaction(self)
        except:
            self._state = STATE_PENDING
            self.enabled = False
            raise

        # Record the start time for transaction.

        self.start_time = time.time()

        # Record initial CPU user time.

        self._cpu_user_time_start = os.times()[0]

        # Calculate initial thread utilisation factor.

        if self._concurrency_model == CONCURRENCY_THREADING:
            thread_instance = threading.currentThread()
            self._thread_utilization = self._application.thread_utilization
            if self._thread_utilization:
                self._thread_utilization.enter_transaction(thread_instance)
                self._thread_utilization_start = \
                        self._thread_utilization.utilization_count()

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

        self._state = STATE_STOPPED

        if not self._settings:
            return

        if not self._dead:
            try:
                self._drop_transaction(self)
            except:
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

        self._cpu_user_time_value = (self._cpu_user_time_end -
                self._cpu_user_time_start)

        if duration:
            self._cpu_utilization_value = self._cpu_user_time_value / (
                    duration * newrelic.core.samplers.cpu_count())
        else:
            self._cpu_utilization_value = 0.0

        # Calculate thread utilisation factor if using.

        if self._thread_utilization:
            self._thread_utilization.exit_transaction()
            if self._thread_utilization_start:
                if not self._thread_utilization_end:
                    self._thread_utilization_end = (
                            self._thread_utilization.utilization_count())
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
        self.record_metric('Python/WSGI/Input/Time', read_duration)

        sent_duration = 0
        if self._sent_start:
            if not self._sent_end:
                self._sent_end = time.time()
            sent_duration = self._sent_end - self._sent_start
            metrics['WSGI/Output/Time'] = '%.4f' % sent_duration
        self.record_metric('Python/WSGI/Output/Time',
                           sent_duration)

        if self.queue_start:
            queue_wait = self.start_time - self.queue_start
            if queue_wait < 0:
                queue_wait = 0
            metrics['WebFrontend/QueueTime'] = '%.4f' % queue_wait

        self.record_metric('Python/WSGI/Input/Bytes',
                           self._bytes_read)

        self.record_metric('Python/WSGI/Input/Calls/read',
                           self._calls_read)
        self.record_metric('Python/WSGI/Input/Calls/readline',
                           self._calls_readline)
        self.record_metric('Python/WSGI/Input/Calls/readlines',
                           self._calls_readlines)

        self.record_metric('Python/WSGI/Output/Bytes',
                           self._bytes_sent)
        self.record_metric('Python/WSGI/Output/Calls/yield',
                           self._calls_yield)
        self.record_metric('Python/WSGI/Output/Calls/write',
                           self._calls_write)

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
                guid=self.rum_guid,
                cpu_utilization=self._cpu_utilization_value,
                suppress_transaction_trace=self.suppress_transaction_trace)

        # Clear settings as we are all done and don't
        # need it anymore.

        self._settings = None
        self.enabled = False

        if not self.ignore_transaction:
            self._application.record_transaction(node)

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

    def _freeze_path(self):
        if self._frozen_path is None:
            self._priority = None

            if self._group == 'Uri':
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

            self.apdex = (self._settings.web_transactions_apdex.get(self.path)
                    or self._settings.apdex_t)

    def name_transaction(self, name, group=None, priority=None):

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

        if group is None:
            group = 'Function'

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

        if type(name) == type(''):
            name = name.decode('Latin-1')

        self._group = group
        self._name = name

    def record_exception(self, exc, value, tb, params={}, ignore_errors=[]):

        # Bail out if the transaction is not active or
        # collection of errors not enabled.

        if not self._settings:
            return

        settings = self._settings
        error_collector = settings.error_collector

        if not error_collector.enabled or not settings.collect_errors:
            return

        # Has to be an error to be logged.

        if exc is None or value is None or tb is None:
            return

        module = value.__class__.__module__
        name = value.__class__.__name__

        # We need to check for module.name and module:name.
        # Originally we used module.class but that was
        # inconsistent with everything else which used
        # module:name. So changed to use ':' as separator, but
        # for backward compatability need to support '.' as
        # separator for time being.

        if module:
            fullname = '%s:%s' % (module, name)
        else:
            fullname = name

        if fullname in ignore_errors:
            return

        if fullname in error_collector.ignore_errors:
            return

        if module:
            fullname = '%s.%s' % (module, name)
        else:
            fullname = name

        if fullname in ignore_errors:
            return

        if fullname in error_collector.ignore_errors:
            return

        # Only remember up to limit of what can be caught for a
        # single transaction. This could be trimmed further
        # later if there are already recorded errors and would
        # go over the harvest limit.

        if len(self._errors) >= settings.agent_limits.errors_per_transaction:
            return

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
                message = unicode(value)
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
            if error.type == exc_type and error.message == message:
                return

        stack_trace = traceback.format_exception(exc, value, tb)

        node = newrelic.core.error_node.ErrorNode(
                timestamp=time.time(),
                type=exc_type,
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
        warnings.warn('Internal API change. Use record_transaction() '
                'instead of notice_error().', DeprecationWarning,
                stacklevel=2)

        self.record_exception(exc, value, tb, params, ignore_errors)

    def record_metric(self, name, value):
        self._custom_metrics.record_value_metric(
                ValueMetric(name=name, value=value))

    def _parent_node(self):
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
        if type(node) is newrelic.core.database_node.DatabaseNode:
            settings = self._settings
            if not settings.collect_traces:
                return
            if not settings.slow_sql.enabled:
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

        if self._thread_utilization:
            if self._thread_utilization_start:
                if not self._thread_utilization_end:
                    self._thread_utilization_end = (
                            self._thread_utilization.utilization_count())

        self._cpu_user_time_end = os.times()[0]

    def add_custom_parameter(self, name, value):
        self._custom_params[name] = value

    def add_custom_parameters(self, items):
        for name, value in items:
            self._custom_params[name] = value

    def add_user_attribute(self, name, value):
        self._user_attrs[name] = value

    def add_user_attributes(self, items):
        for name, value in items:
            self._user_attrs[name] = value

    def dump(self, file):
        """Dumps details about the transaction to the file object."""

        print >> file, 'Application: %s' % (
                self.application.name)
        print >> file, 'Time Started: %s' % (
                time.asctime(time.localtime(self.start_time)))
        print >> file, 'Thread Id: %r' % (
                self._thread_id,)
        print >> file, 'Concurrency Model: %r' % (
                self._concurrency_model,)
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
    current = Transaction._current_transaction()
    if current and (current.ignore_transaction or current.stopped):
        return None
    return current

def transaction():
    warnings.warn('Internal API change. Use current_transaction() '
            'instead of transaction().', DeprecationWarning, stacklevel=2)

    return current_transaction()
