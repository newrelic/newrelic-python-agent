from benchmarks.util import MockApplication

import newrelic.core.transaction_cache as transaction_cache
from newrelic.api.transaction import Transaction


# a black hole... anything that enters will never again emerge...
# newrelic.core.transaction_cache._transaction_cache._cache is overloaded with
# an instance of this object so that we can repeatedly insert the same
# transaction without throwing an error.
class VoidDict(dict):
    def __setitem__(self, key, item):
        pass


STATE_PENDING = Transaction.STATE_PENDING


class Suite(object):
    def setup(self):
        app = MockApplication()
        transaction_cache._transaction_cache._cache = VoidDict()
        self.transaction = Transaction(app)

    def teardown(self):
        transaction_cache._transaction_cache._cache = {}

    def time_enter(self):
        self.transaction.__enter__()
        self.transaction._state = STATE_PENDING
