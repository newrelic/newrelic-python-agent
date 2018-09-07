import sys
import newrelic.api.transaction as transaction
from benchmarks.util import MockApplication, MockTransactionCache
transaction_cache = transaction.transaction_cache


class TimeSuite:

    def setup(self):
        transaction.transaction_cache = MockTransactionCache
        app = MockApplication()
        self.transaction = transaction.Transaction(app)
        self.transaction.__enter__()
        self.settings = app.settings
        try:
            raise ValueError("oops!")
        except ValueError:
            self.exc_info = sys.exc_info()

    def teardown(self):
        transaction.transaction_cache = transaction_cache

    def time_exit_no_error(self):
        self.transaction.enabled = True
        self.transaction._settings = self.settings
        self.transaction.__exit__(None, None, None)

    def time_exit_with_error(self):
        self.transaction.enabled = True
        self.transaction._settings = self.settings
        self.transaction.__exit__(*self.exc_info)
