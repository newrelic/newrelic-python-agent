from newrelic.api.transaction import current_transaction
from newrelic.core.trace_cache import trace_cache
from benchmarks.util import MockApplication, MockTransaction


class Suite(object):
    def setup(self):
        app = MockApplication()
        self.transaction = MockTransaction(app)
        self.transaction.thread_id = trace_cache().current_thread_id()
        self.transaction.ignore_transaction = False
        self.transaction.save_transaction()

    def teardown(self):
        self.transaction.drop_transaction()

    def time_current_transaction_active(self):
        current_transaction(active_only=True)

    def time_current_transaction_inactive(self):
        current_transaction(active_only=False)
