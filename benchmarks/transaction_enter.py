from benchmarks.util import MockApplication

import newrelic.core.transaction_cache
from newrelic.api.background_task import BackgroundTask


# a black hole... anything that enters will never again emerge...
# newrelic.core.transaction_cache._transaction_cache._cache is overloaded with
# an instance of this object so that we can repeatedly insert the same
# transaction without throwing an error.
class VoidDict(dict):
    def __setitem__(self, key, item):
        pass


class Suite:
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
