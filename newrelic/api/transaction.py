import os
import time
import weakref
import threading
import traceback
import collections

import newrelic.core.transaction

import newrelic.core.config

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

STATE_PENDING = 0
STATE_RUNNING = 1
STATE_STOPPED = 2

class DummyTransaction(object):

    def __init__(self):
        self._children = []

class Transaction(object):

    _local = threading.local()

    @classmethod
    def _current_transaction(cls):
        if hasattr(cls._local, 'current'):
            return cls._local.current()

    @classmethod
    def _save_transaction(cls, transaction):
        if hasattr(cls._local, 'current'):
            raise RuntimeError('transaction already active')

	# Cache the transaction using a weakref so that
	# the transaction can still be deleted and the
	# destructor can call __exit__() if necessary if
	# transaction still running. If don't use a
	# weakref then will have a object reference
	# cycle and transaction will never be destroyed.

        cls._local.current = weakref.ref(transaction)

    @classmethod
    def _drop_transaction(cls, transaction):
        if not hasattr(cls._local, 'current'):
            raise RuntimeError('no activate transaction')

        current = cls._local.current()

	# If the reference returned from the weakref is
	# None, then can only assume that __exit__()
	# wasn't called on transaction prior to it being
	# deleted. In that case we don't raise an
	# exception and just remove the cache weakref
	# object for the current thread.

        if current and transaction != current:
            raise RuntimeError('not the current transaction')

        del cls._local.current

    def __init__(self, application, enabled=None):

        self._application = application

        self._state = STATE_PENDING
        self._settings = None

        self._group = None
        self._name = None

        self._node_stack = collections.deque()

        self._request_uri = None

        self._queue_start = 0.0
        self._start_time = 0.0
        self._end_time = 0.0

        self._errors = []
        self._slow_sql = []

        self.custom_parameters = {}
        self.request_parameters = {}

        self.background_task = False

        self.enabled = False
        self.ignore = False
        self.ignore_apdex = False
        self.coroutines = False
        self.capture_params = True
        self.ignored_params = []
        self.response_code = 0

        global_settings = newrelic.core.config.global_settings()

        if global_settings.monitor_mode:
            if enabled or (enabled is None and application.enabled):
                self.enabled = True

    def __del__(self):
        if self._state == STATE_RUNNING:
            self.__exit__(None, None, None)

    def __enter__(self):

        assert(self._state == STATE_PENDING)

        # Bail out if the transaction is not enabled.

        if not self.enabled:
            return self

	# Cache transaction in thread/coroutine local
	# storage so that it can be accessed from
	# anywhere in the context of the transaction.
        # This is done even though transaction will
        # not collect data because application is not
        # active.

        self._save_transaction(self)

	# Mark transaction as active and update state
        # used to validate correct usage of class.

        self._state = STATE_RUNNING

	# Bail out if the application isn't marked as
	# active. An application isn't active if we
	# cannot retrieve a settings object for it. If
	# not activate we try and activate it. We cache
	# the settings object so we know it will not
	# dissapear during the life of the transaction
	# and so can be used by anything executing
	# within the context of the transaction.

        self._settings = self._application.settings

        if not self._settings:
            #self._application.activate()
            return self

        # Record the start time for transaction.

        self._start_time = time.time()

	# We need to push an object onto the top of the
	# node stack so that children can reach back and
	# add themselves as children to the parent. We
	# can't use ourself though as we then end up
	# with a reference count cycle which will cause
	# the destructor to never be called if the
	# __exit__() function is never called. We
	# instead push on to the top of the node stack a
	# dummy root transaction object and when done we
	# will just grab what we need from that.

        self._node_stack.append(DummyTransaction())

        return self

    def __exit__(self, exc, value, tb):

        # Bail out if the transaction is not enabled.

        if not self.enabled:
            return

	# Mark as stopped and drop the transaction from
	# thread/coroutine local storage.

        self._state = STATE_STOPPED
        self._drop_transaction(self)

        if not self._settings:
            return

        # Record error if one was registered.

        if exc is not None and value is not None and tb is not None:
            self.notice_error(exc, value, tb)

        # Record the end time for transaction.

        self._end_time = time.time()

        children = self._node_stack.pop()._children

        # Derive generated values from the raw data.

        duration = self._end_time - self._start_time

        exclusive = duration
        for child in children:
            exclusive -= child.duration
        exclusive = max(0, exclusive)

	# Construct final root node of transaction trace.

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

        node = newrelic.core.transaction.TransactionNode(
                type=type,
                group=group,
                name=self._name,
                request_uri=self._request_uri,
                response_code=self.response_code,
                request_params=self.request_parameters,
                custom_params=self.custom_parameters,
                queue_start=self._queue_start,
                start_time=self._start_time,
                end_time=self._end_time,
                duration=duration,
                exclusive=exclusive,
                children=tuple(children),
                errors=tuple(self._errors),
                slow_sql=tuple(self._slow_sql),
                apdex_t=self._settings.apdex_t,
                ignore_apdex=self.ignore_apdex)

        # Clear settings as we are all done and don't
        # need it anymore.

        self._settings = None

        self._application.record_transaction(node)

    @property
    def state(self):
        return self._state

    @property
    def settings(self):
        return self._settings

    @property
    def active(self):
        return self._settings is not None

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
        """For backwards compatibility with unit tests."""
        name = self._name
        if name is None:
            name = '<unknown>'
        if self._group in ['Uri', None]:
            return name
        else:
            return '%s/%s' % (self._group, name)

    def name_transaction(self, name, group=None):

	# Always perform this operation even if the
	# transaction is not active at the time as will
	# be called from constructor.

        if group is None:
            group = 'Function'

        self._group = group
        self._name = name

    def notice_error(self, exc, value, tb, params={}):

	# Bail out if the transaction is not active.

        if not self._settings:
            return

        # Has to be an error to be logged.

        if exc is None or value is None or tb is None:
            return

        # XXX Need to ignore if listed to be ignore in
        # settings.

	# XXX Need to capture source if enabled in
	# settings.

        type = exc.__name__
        message = value
        stack_trace = traceback.format_exception(exc, value, tb)

        node = newrelic.core.transaction.ErrorNode(
                type=exc.__name__,
                message=str(value),
                stack_trace=traceback.format_exception(exc, value, tb),
                custom_params=params,
                file_name=None,
                line_number=None,
                source=None)

        self._errors.append(node)

def transaction():
    return Transaction._current_transaction()

if _agent_mode not in ('julunggul',):
    import _newrelic
    transaction = _newrelic.transaction
