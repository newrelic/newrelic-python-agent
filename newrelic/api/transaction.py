import os
import weakref
import threading

import newrelic.api.settings

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

PENDING = 0
RUNNING = 1
STOPPED = 2

class Transaction(object):

    _local = threading.local()

    @classmethod
    def _current_transaction(cls):
        if hasattr(cls._local, 'current'):
            return cls._local.current()

    @classmethod
    def _push_transaction(cls, transaction):
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
    def _pop_transaction(cls, transaction):
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

        self._state = PENDING

        self._path = '<unknown>'

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

        settings = newrelic.api.settings.settings()

        if settings.monitor_mode:
            if enabled or (enabled is None and application.enabled):
                self.enabled = True

    def __del__(self):
        if self._state == RUNNING:
            self.__exit__(None, None, None)

    def __enter__(self):
        self._push_transaction(self)
        self._state = RUNNING

    def __exit__(self, exc, value, tb):
        if self._state != RUNNING:
            return
        self._state = STOPPED
        self._pop_transaction(self)

    @property
    def state(self):
        return self._state

    @property
    def application(self):
        return self._application

    @property
    def path(self):
        return self._path

    def name_transaction(self, name, prefix='Function'):
        self._path = "%s/%s" % (prefix, name)

    def notice_error(self, exc, value, tb, params={}):
        pass

def transaction():
    return Transaction._current_transaction()

if _agent_mode not in ('julunggul',):
    import _newrelic
    transaction = _newrelic.transaction
