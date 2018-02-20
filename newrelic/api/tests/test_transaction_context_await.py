import sys
import newrelic.tests.test_cases

import newrelic.api.application

application = newrelic.api.application.application_instance()

code = """
from newrelic.api.transaction import current_transaction
import newrelic.api.transaction_context as transaction_context
import asyncio

async def basic_async_coroutine(txn):
    assert current_transaction() is txn
    await asyncio.sleep(0)
    assert current_transaction() is txn


class TestAsyncCoroutineTransactionContext(newrelic.tests.test_cases.TestCase):

    def test_coroutine_transaction_context_await(self):
        async def _test():
            txn = newrelic.api.background_task.BackgroundTask(application,
                    'test_coroutine_transaction_context_await')

            with txn:
                coro = basic_async_coroutine(txn)
                coro = transaction_context.CoroutineTransactionContext(coro,
                        txn)

                # remove transaction from cache
                txn.drop_transaction()

                try:
                    # consume coroutine
                    await coro
                finally:
                    # put transaction back
                    txn.save_transaction()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(_test())
"""

if sys.version_info >= (3, 5):
    exec(code)
