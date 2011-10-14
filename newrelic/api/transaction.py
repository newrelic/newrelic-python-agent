from __future__ import with_statement

import sys
import time
import weakref
import threading
import traceback

import newrelic.core.config

import newrelic.core.transaction_node
import newrelic.core.error_node

import newrelic.api.time_trace

STATE_PENDING = 0
STATE_RUNNING = 1
STATE_STOPPED = 2

class Transaction(object):

    _transactions = weakref.WeakValueDictionary()

    @classmethod
    def _current_thread(cls):
        greenlet = sys.modules.get('greenlet')

        if greenlet:
            try:
                return greenlet.getcurrent()
            except:
                pass

        return threading.currentThread()

    @classmethod
    def _current_transaction(cls):
        thread = cls._current_thread()
        return cls._transactions.get(thread)

    @classmethod
    def _save_transaction(cls, transaction):
        thread = cls._current_thread()
        if thread in cls._transactions:
            raise RuntimeError('transaction already active')

        cls._transactions[thread] = transaction

    @classmethod
    def _drop_transaction(cls, transaction):
        thread = cls._current_thread()
        if not thread in cls._transactions:
            raise RuntimeError('no activate transaction')

        current = cls._transactions.get(thread)

        if transaction != current:
            raise RuntimeError('not the current transaction')

        del cls._transactions[thread]

    def __init__(self, application, enabled=None):

        self._application = application

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

        self._custom_params = {}
        self._request_params = {}

        self.background_task = False

        self.enabled = False
        self.ignore = False
        self.ignore_apdex = False
        self.coroutines = False
        self.capture_params = True
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
            self._drop_transaction(self)

        # Record error if one was registered.

        if exc is not None and value is not None and tb is not None:
            self.notice_error(exc, value, tb)

        # Record the end time for transaction.

        if not self.stopped:
            self.end_time = time.time()

        root = self._node_stack.pop()
        children = root.children

        # Derive generated values from the raw data. The
        # dummy root node has exclusive time of children
        # as negative number. Add our own duration to get
        # our own exclusive time.

        duration = self.end_time - self.start_time

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
            self._custom_params['STATUS'] = str(self.response_code)

        node = newrelic.core.transaction_node.TransactionNode(
                settings=self._settings,
                path=self.path,
                type=type,
                group=group,
                name=self._name,
                request_uri=self._request_uri,
                response_code=self.response_code,
                request_params=self._request_params,
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
                ignore_apdex=self.ignore_apdex,
                custom_metrics=self._custom_metrics)

        # Clear settings as we are all done and don't
        # need it anymore.

        self._settings = None
        self.enabled = False

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
                name = self._application.normalize_name(self._name)
                if self._name != name:
                    self._group = 'NormalizedUri'
                    self._name = name

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
                type=type,
                message=message,
                stack_trace=stack_trace,
                custom_params=custom_params,
                file_name=None,
                line_number=None,
                source=None)

        # TODO Errors are recorded in time order. If
        # there are two exceptions of same time and
        # different message, the UI displays the
        # first one. In the PHP agent it was
        # recording the errors in reverse time order
        # and so the UI displayed the last one. What
        # is the the official order in which they
        # should be sent.

        self._errors.append(node)

    def record_metric(self, name, value):
        self._custom_metrics.append((name, value))

    def _push_current(self, node):
        self._node_stack.append(node)

    def _pop_current(self, node):
        last = self._node_stack.pop()
        assert last == node
        parent = self._node_stack[-1]
        return parent

    def _process_node(self, node):
        pass

        # TODO Need to incorporate slow SQL tracking.

        #if transaction_tracer.enabled and settings.collect_traces:
        #    if duration >= transaction_tracer.stack_trace_threshold:
        #        self.transaction._slow_sql.append(node)

    def stop_recording(self):
        if not self.enabled:
            return

        if self.stopped:
            return

        if self.end_time:
            return

        self.end_time = time.time()
        self.stopped = True

    def add_custom_parameter(self, name, value):
        self._custom_params[name] = value

    def add_custom_parameters(self, items):
        for name, value in items:
            self._custom_params[name] = value

def transaction():
    current = Transaction._current_transaction()
    if current and current.stopped:
        return None
    return current
