import newrelic.core.transaction_cache
from newrelic.api.background_task import BackgroundTask


class MockApplication(object):
    def __init__(self, name='Python Application'):
        from newrelic.core.config import finalize_application_settings

        self.global_settings = finalize_application_settings()
        self.global_settings.enabled = True
        self.settings = finalize_application_settings({})
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
        self.attribute_filter = None

    def activate(self):
        pass

    def normalize_name(self, name, rule_type):
        return name, False

    def record_transaction(self, data, *args):
        return None

    def compute_sampled(self, priority):
        return True


# a black hole... anything that enters will never again emerge...
# newrelic.core.transaction_cache._transaction_cache._cache is overloaded with
# an instance of this object so that we can repeatedly insert the same
# transaction without throwing an error.
class VoidDict(dict):
    def __setitem__(self, key, item):
        pass


class TransactionEnterSuite:
    def setup(self):
        app = MockApplication()
        newrelic.core.transaction_cache._transaction_cache._cache = VoidDict()
        self.transaction = BackgroundTask(app, 'foo')

    def teardown(self):
        newrelic.core.transaction_cache._transaction_cache._cache = {}

    def time_enter(self):
        self.transaction.__enter__()
        self.transaction._state = self.transaction.STATE_PENDING

    def time_state_reassignment(self):
        self.transaction._state = self.transaction.STATE_PENDING
