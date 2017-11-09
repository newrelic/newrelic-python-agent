import unittest

import newrelic.api.application
import newrelic.api.background_task
import newrelic.api.transaction_context
import newrelic.tests.test_cases
from newrelic.api.transaction import current_transaction

application = newrelic.api.application.application_instance()


class TestCase(newrelic.tests.test_cases.TestCase):

    def test_transaction_context_basic(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_transaction_context_basic')

        assert current_transaction(active_only=False) is None

        with newrelic.api.transaction_context.TransactionContext(txn):
            assert current_transaction(active_only=False) is txn

        assert current_transaction(active_only=False) is None

    def test_transaction_context_swaps_transactions(self):
        with newrelic.api.background_task.BackgroundTask(application,
                'test_transaction_context_swaps_transactions') as txn:
            other = newrelic.api.background_task.BackgroundTask(application,
                    'temp_other')

            assert current_transaction(active_only=False) is txn

            with newrelic.api.transaction_context.TransactionContext(other):
                assert current_transaction(active_only=False) is other

            assert current_transaction(active_only=False) is txn

        assert current_transaction(active_only=False) is None

    def test_transaction_context_removes_transaction(self):
        with newrelic.api.background_task.BackgroundTask(application,
                'test_transaction_context_removes_transaction') as txn:

            assert current_transaction(active_only=False) is txn

            with newrelic.api.transaction_context.TransactionContext(None):
                assert current_transaction(active_only=False) is None

            assert current_transaction(active_only=False) is txn

        assert current_transaction(active_only=False) is None


if __name__ == '__main__':
    unittest.main()
