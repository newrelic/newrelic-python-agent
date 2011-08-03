import os
import time
import weakref
import threading
import collections

import newrelic.core.config

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

STATE_PENDING = 0
STATE_RUNNING = 1
STATE_STOPPED = 2

PATH_TYPE_UNKNOWN = 0
PATH_TYPE_RAW = 1
PATH_TYPE_URI = 2

TransactionNode = collections.namedtuple('TransactionNode',
        ['name', 'children', 'queue_start', 'start_time', 'end_time'])

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

        self._path = '<unknown>'
        self._path_type = PATH_TYPE_UNKNOWN
        
        self._node_stack = collections.deque()
        self._children = []

        self._queue_start = 0.0
        self._start_time = 0.0
        self._end_time = 0.0

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

	# Mark as started and cache transaction in
	# thread/coroutine local storage so that it can
	# be accessed from anywhere in the context of
	# the transaction.

        self._state = STATE_RUNNING
        self._save_transaction(self)

	# Bail out if the transaction is running in a
	# disabled state.
        

        if not self.enabled:
            return

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

        if self._state != STATE_RUNNING:
            return

	# Bail out if the transaction is running in a
	# disabled state. Still need to mark as stopped
	# and drop the transaction from thread/coroutine
	# local storage.

        if not self.enabled:
            self._drop_transaction(self)
            self._state = STATE_STOPPED
            return

        # Record error if one was registered.

        if exc is not None and value is not None and tb is not None:
            self.notice_error(exc, value, tb)

        # Record the end time for transaction.

        self._end_time = time.time()

	# Mark as stopped and drop the transaction from
	# thread/coroutine local storage.

        self._drop_transaction(self)
        self._state = STATE_STOPPED

        children = self._node_stack.pop()._children

	# XXX This mess is because trying to keep some
	# compatibility with what C code was doing.
	# Unfortunately it was doing silly things to get
	# around issues with PHP agent. We will fix this
	# soon by changing C code to something more sane
	# so can keep same tests during transition. :-(

        if self._path_type == PATH_TYPE_URI:
            name = 'Uri/%s' % self._path
        elif self._path_type == PATH_TYPE_RAW:
            name = self._path
        else:
            name = 'Uri/<unknown>'

        nodes = TransactionNode(name=name, children=children,
                queue_start=self._queue_start, start_time=self._start_time,
                end_time=self._end_time)

    @property
    def state(self):
        return self._state

    @property
    def active(self):
        return self.enabled and self._state == STATE_RUNNING

    @property
    def application(self):
        return self._application

    @property
    def path(self):
        return self._path

    def name_transaction(self, name, prefix=None):

	# Bail out if the transaction is running in a
	# disabled state.

        if not self.enabled:
            return

        if prefix is None:
            prefix = 'Function'
        self._path = "%s/%s" % (prefix, name)
        self._path_type = PATH_TYPE_RAW

    def notice_error(self, exc, value, tb, params={}):

	# Bail out if the transaction is running in a
	# disabled state.

        if not self.enabled:
            return

        # Has to be an error to be logged.

        if exc is None or value is None or tb is None:
            return

        # XXX Need to ignore if listed to be ignore in
        # global settings.

        # XXX Need to capture error into list of errors.

def transaction():
    return Transaction._current_transaction()

if _agent_mode not in ('julunggul',):
    import _newrelic
    transaction = _newrelic.transaction
