import asyncio

from newrelic.api.transaction import current_transaction

loop = asyncio.get_event_loop()


def native_coroutine_test(transaction, nr_enabled=True, does_hang=False,
        call_exit=False, runtime_error=False):
    @transaction
    async def task():
        txn = current_transaction()

        if not nr_enabled:
            assert txn is None

        if call_exit:
            txn.__exit__(None, None, None)

        try:
            if does_hang:
                await loop.create_future()
            else:
                await asyncio.sleep(0.0)
        except GeneratorExit:
            if runtime_error:
                await asyncio.sleep(0.0)

        if not call_exit:
            assert current_transaction() is txn

    return task
