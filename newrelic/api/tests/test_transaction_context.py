import unittest
import sys

import newrelic.api.application
import newrelic.api.background_task
import newrelic.api.transaction_context as transaction_context
import newrelic.tests.test_cases
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction

application = newrelic.api.application.application_instance()


class TestTransactionContext(newrelic.tests.test_cases.TestCase):

    def test_exited_transaction_is_not_swapped_in(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_exited_transaction_is_not_swapped_in')

        with txn:
            context = transaction_context.TransactionContext(txn)

        with context:
            assert current_transaction(active_only=False) is None

    def test_exited_transaction_is_not_restored(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_exited_transaction_is_not_restored')

        txn.__enter__()
        context = transaction_context.TransactionContext(None)
        with context:
            txn.save_transaction()
            txn.__exit__(None, None, None)

        assert current_transaction(active_only=False) is None

    def test_exited_trace_is_not_restored(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_exited_trace_is_not_restored')

        with txn:
            trace = FunctionTrace(txn, 'foobar')
            trace.__enter__()
            try:
                txn.drop_transaction()

                with transaction_context.TransactionContext(txn):
                    trace.__exit__(None, None, None)

                assert txn.current_span is not trace
            finally:
                txn.save_transaction()

    def test_trace_is_restored(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_trace_is_restored')

        with txn:
            trace = FunctionTrace(txn, 'foobar')
            trace.__enter__()
            try:
                txn.drop_transaction()

                with transaction_context.TransactionContext(txn):
                    assert txn.current_span is trace

                assert txn.current_span is trace
            finally:
                txn.save_transaction()

    def test_target_transaction_is_not_active(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_target_transaction_is_not_active')

        with txn:
            txn.stop_recording()
            txn.drop_transaction()
            try:
                with transaction_context.TransactionContext(txn):
                    assert current_transaction(active_only=False) is txn
            finally:
                txn.save_transaction()

    def test_source_transaction_is_not_active(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_source_transaction_is_not_active')

        with txn:
            txn.stop_recording()
            txn.drop_transaction()
            try:
                with transaction_context.TransactionContext(None):
                    assert current_transaction(active_only=False) is None
            finally:
                txn.save_transaction()

            assert txn.stopped
            assert current_transaction(active_only=False) is txn

    def test_swapping_same_inactive_transaction(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_swapping_same_inactive_transaction')

        with txn:
            txn.stop_recording()

            with transaction_context.TransactionContext(txn):
                assert current_transaction(active_only=False) is txn

            assert current_transaction(active_only=False) is txn

    def test_swapping_same_active_transaction(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_swapping_same_active_transaction')

        with txn:
            with transaction_context.TransactionContext(txn):
                assert current_transaction(active_only=False) is txn

            assert current_transaction(active_only=False) is txn

    def test_enter_returns_self(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_enter_returns_self')

        context = transaction_context.TransactionContext(txn)

        with context as _context:
            assert context is _context

    def test_transaction_context_basic(self):
        txn = newrelic.api.background_task.BackgroundTask(application,
                'test_transaction_context_basic')

        assert current_transaction(active_only=False) is None

        with transaction_context.TransactionContext(txn):
            assert current_transaction(active_only=False) is txn

        assert current_transaction(active_only=False) is None

    def test_transaction_context_swaps_transactions(self):
        with newrelic.api.background_task.BackgroundTask(application,
                'test_transaction_context_swaps_transactions') as txn:
            other = newrelic.api.background_task.BackgroundTask(application,
                    'temp_other')

            assert current_transaction(active_only=False) is txn

            with transaction_context.TransactionContext(other):
                assert current_transaction(active_only=False) is other

            assert current_transaction(active_only=False) is txn

        assert current_transaction(active_only=False) is None

    def test_transaction_context_removes_transaction(self):
        with newrelic.api.background_task.BackgroundTask(application,
                'test_transaction_context_removes_transaction') as txn:

            assert current_transaction(active_only=False) is txn

            with transaction_context.TransactionContext(None):
                assert current_transaction(active_only=False) is None

            assert current_transaction(active_only=False) is txn

        assert current_transaction(active_only=False) is None


if sys.version_info >= (3, 4):
    import asyncio

    @asyncio.coroutine
    def basic_coroutine(txn):
        assert current_transaction() is txn
        yield
        assert current_transaction() is txn

    @asyncio.coroutine
    def catches_exc_coroutine(txn):
        for i in range(3):
            assert current_transaction() is txn
            try:
                yield
            except:
                pass
            assert current_transaction() is txn

    class TestCoroutineTransactionContext(newrelic.tests.test_cases.TestCase):

        def test_coroutine_transaction_context_basic(self):
            txn = newrelic.api.background_task.BackgroundTask(application,
                    'test_coroutine_transaction_context_basic')

            with txn:
                coro = basic_coroutine(txn)
                coro = transaction_context.CoroutineTransactionContext(coro,
                        txn)

                # remove transaction from cache
                txn.drop_transaction()

                try:
                    # consume coroutine
                    for _ in coro:
                        pass
                finally:
                    # put transaction back
                    txn.save_transaction()

        def test_coroutine_transaction_context_uncaught_throw(self):
            txn = newrelic.api.background_task.BackgroundTask(application,
                    'test_coroutine_transaction_context_uncaught_throw')

            with txn:
                coro = basic_coroutine(txn)
                coro = transaction_context.CoroutineTransactionContext(coro,
                        txn)

                # remove transaction from cache
                txn.drop_transaction()

                try:
                    # kickstart the coroutine (at yield)
                    next(coro)

                    with self.assertRaises(ValueError):
                        # Throw an uncaught exception
                        coro.throw(ValueError)

                    # consume the coroutine
                    assert list(coro) == []

                finally:
                    # put transaction back
                    txn.save_transaction()

        def test_coroutine_transaction_context_caught_throw(self):
            txn = newrelic.api.background_task.BackgroundTask(application,
                    'test_coroutine_transaction_context_caught_throw')

            with txn:
                coro = catches_exc_coroutine(txn)
                coro = transaction_context.CoroutineTransactionContext(coro,
                        txn)

                # remove transaction from cache
                txn.drop_transaction()

                try:
                    # kickstart the coroutine (at yield)
                    next(coro)

                    # Throw a caught exception
                    coro.throw(ValueError)

                    # the coroutine should still be open for consumption
                    next(coro)

                    # consume the coroutine
                    assert list(coro) == []
                finally:
                    # put transaction back
                    txn.save_transaction()

        def test_coroutine_transaction_context_close(self):
            txn = newrelic.api.background_task.BackgroundTask(application,
                    'test_coroutine_transaction_context_uncaught_throw')

            with txn:
                coro = basic_coroutine(txn)
                coro = transaction_context.CoroutineTransactionContext(coro,
                        txn)

                # remove transaction from cache
                txn.drop_transaction()

                try:
                    # kickstart the coroutine (at yield)
                    next(coro)

                    coro.close()
                finally:
                    # put transaction back
                    txn.save_transaction()


if __name__ == '__main__':
    unittest.main()
