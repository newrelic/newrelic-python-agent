from __future__ import with_statement

import os
import sys
import time
import weakref
import threading
import traceback
import logging

try:
    from mod_wsgi import thread_utilization as _thread_utilization
    from mod_wsgi import threads_per_process as _threads_per_process
except:
    _thread_utilization = None

import newrelic.core.config

import newrelic.core.transaction_node
import newrelic.core.database_node
import newrelic.core.error_node
import newrelic.core.samplers

import newrelic.api.time_trace


_logger = logging.getLogger(__name__)

STATE_PENDING = 0
STATE_RUNNING = 1
STATE_STOPPED = 2

class Transaction(object):

    _transactions = weakref.WeakValueDictionary()

    @classmethod
    def _current_coroutine(cls):
        meinheld = sys.modules.get('meinheld.server')

        if meinheld:
            try:
                result = meinheld.get_ident()
                if result is not None:
                    return result
            except:
                pass

        greenlet = sys.modules.get('greenlet')

        if greenlet:
            try:
                return greenlet.getcurrent()
            except:
                pass

    @classmethod
    def _current_thread(cls):
        return threading.currentThread()

    @classmethod
    def _current_context(cls):
        return (cls._current_thread(), cls._current_coroutine())

    @classmethod
    def _current_transaction(cls):
        active_context = cls._current_context()
        return cls._transactions.get(active_context)

    @classmethod
    def _save_transaction(cls, transaction):
        active_context = cls._current_context()

        if active_context in cls._transactions:
            raise RuntimeError('transaction already active')

        cls._transactions[active_context] = transaction
        transaction._active_context = active_context

    @classmethod
    def _drop_transaction(cls, transaction):
        active_context = transaction._active_context

        if not active_context in cls._transactions:
            raise RuntimeError('no active transaction')

        current = cls._transactions.get(active_context)

        if transaction != current:
            raise RuntimeError('not the current transaction')

        transaction._active_context = None
        del cls._transactions[active_context]

    def __init__(self, application, enabled=None):

        self._application = application

        self._active_context = None

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
        self._request_params = {}

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

        self.capture_params = False
        self.ignored_params = []

        self.response_code = 0

        self._custom_metrics = []

        global_settings = newrelic.core.config.global_settings()

        if global_settings.monitor_mode:
            if enabled or (enabled is None and application.enabled):
                self._settings = self._application.settings
                if not self._settings:
                    self._application.activate()
                else:
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

        self._save_transaction(self)

        # Record initial CPU user time.

        #self._cpu_user_time_start = os.times()[0]

        # Calculate initial thread utilisation factor
        # if using mod_wsgi.

        if _thread_utilization:
            self._thread_utilization_start = _thread_utilization()

        # Record the start time for transaction.

        self.start_time = time.time()

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
            self.notice_error(exc, value, tb)

        # Record the end time for transaction and then
        # calculate the duration.

        if not self.stopped:
            self.end_time = time.time()

        duration = self.end_time - self.start_time

        # Calculate thread utilisation factor if using
        # mod_wsgi.

        if self._thread_utilization_start:
            if not self._thread_utilization_end:
                self._thread_utilization_end = _thread_utilization()
            self._thread_utilization_value = (self._thread_utilization_end -
                    self._thread_utilization_start) / duration

        # Calculate overall user time.

        #if not self._cpu_user_time_end:
        #    self._cpu_user_time_end = os.times()[0]
        #self._cpu_user_time_value = (self._cpu_user_time_end -
        #        self._cpu_user_time_start)
        #self._cpu_utilization_value = self._cpu_user_time_value / (
        #        duration * newrelic.core.samplers.cpu_count())

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
            type = 'OtherTransaction'
        else:
            type = 'WebTransaction'

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
            metrics['WSGI/Thread/Utilization'] = \
                    '%.6f' % self._thread_utilization_value
            metrics['WSGI/Thread/Count'] = _threads_per_process

        #metrics['CPU/User Time'] = '%.6f' % self._cpu_user_time_value
        #metrics['CPU/Utilization'] = '%.6f' % self._cpu_utilization_value

        read_duration = 0
        if self._read_start:
            read_duration = self._read_end - self._read_start
            metrics['WSGI/Input/Time'] = '%.6f' % read_duration
        self.record_metric('Supportability/WSGI/Input/Time',
                           read_duration)

        sent_duration = 0
        if self._sent_start:
            if not self._sent_end:
                self._sent_end = time.time()
            sent_duration = self._sent_end - self._sent_start
            metrics['WSGI/Output/Time'] = '%.6f' % sent_duration
        self.record_metric('Supportability/WSGI/Output/Time',
                           sent_duration)

        if self.queue_start:
            queue_wait = self.start_time - self.queue_start
            if queue_wait < 0:
                queue_wait = 0
            metrics['WebFrontend/QueueTime'] = '%.6f' % queue_wait

        self.record_metric('Supportability/WSGI/Input/Bytes',
                           self._bytes_read)

        self.record_metric('Supportability/WSGI/Input/Calls/read',
                           self._calls_read)
        self.record_metric('Supportability/WSGI/Input/Calls/readline',
                           self._calls_readline)
        self.record_metric('Supportability/WSGI/Input/Calls/readlines',
                           self._calls_readlines)

        self.record_metric('Supportability/WSGI/Output/Bytes',
                           self._bytes_sent)
        self.record_metric('Supportability/WSGI/Output/Calls/yield',
                           self._calls_yield)
        self.record_metric('Supportability/WSGI/Output/Calls/write',
                           self._calls_write)

        request_params = {}
        parameter_groups = {}

        if self.capture_params:
            request_params = self._request_params

        if self._request_environment:
            parameter_groups['Request environment'] = self._request_environment
        if self._response_properties:
            parameter_groups['Response properties'] = self._response_properties

        #if self._transaction_metrics:
        #    parameter_groups['Transaction metrics'] = self._transaction_metrics

        node = newrelic.core.transaction_node.TransactionNode(
                settings=self._settings,
                path=self.path,
                type=type,
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
                apdex_t=self._settings.apdex_t,
                suppress_apdex=self.suppress_apdex,
                custom_metrics=self._custom_metrics,
                parameter_groups=parameter_groups)

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
            type = 'OtherTransaction'
        else:
            type = 'WebTransaction'

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
            path = '%s/%s%s' % (type, group, name)
        else:
            path = '%s/%s/%s' % (type, group, name)

        return path

    def _freeze_path(self):
        if self._frozen_path is None:
            self._priority = None

            if self._group == 'Uri':
                name, ignore = self._application.normalize_name(self._name)
                if self._name != name:
                    self._group = 'NormalizedUri'
                    self._name = name
                self.ignore_transaction = self.ignore_transaction or ignore

            self._frozen_path = self.path

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

    def notice_error(self, exc, value, tb, params={}, ignore_errors=[]):

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

        # XXX Need to capture source if enabled in
        # settings.

        module = value.__class__.__module__
        name = value.__class__.__name__

        if module:
            fullname = '%s.%s' % (module, name)
        else:
            fullname = name

        if fullname in ignore_errors:
            return

        if fullname in error_collector.ignore_errors:
            return

        if params:
            custom_params = dict(self._custom_params)
            custom_params.update(params)
        else:
            custom_params = self._custom_params

        type = exc.__name__

        try:
            message = str(value)
        except Exception:
            try:
                # Assume JSON encoding can handle unicode.
                message = unicode(value)
            except Exception:
                message = '<unprintable %s object>' % type(value).__name__

        stack_trace = traceback.format_exception(exc, value, tb)

        # Check that we have not recorded this exception
        # previously for this transaction due to multiple
        # error traces triggering. This is not going to be
        # exact but the UI hides exceptions of same type
        # anyway. Better that we under count exceptions of
        # same type and message rather than count same one
        # multiple times.

        for error in self._errors:
            if error.type == type and error.message == message:
                return

        node = newrelic.core.error_node.ErrorNode(
                timestamp=time.time(),
                type=type,
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

    def record_metric(self, name, value):
        self._custom_metrics.append((name, value))

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

        if self._thread_utilization_start:
            if not self._thread_utilization_end:
                self._thread_utilization_end = _thread_utilization()

        #self._cpu_user_time_end = os.times()[0]

    def add_custom_parameter(self, name, value):
        self._custom_params[name] = value

    def add_custom_parameters(self, items):
        for name, value in items:
            self._custom_params[name] = value

    def dump(self, file):
        """Dumps details about the transaction to the file object."""

        print >> file, 'Application: %s' % (
                self.application.name)
        print >> file, 'Time Started: %s' % (
                time.asctime(time.localtime(self.start_time)))
        print >> file, 'Active Context: %r' % (
                self._active_context,)
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


def transaction():
    current = Transaction._current_transaction()
    if current and (current.ignore_transaction or current.stopped):
        return None
    return current
