import asyncio
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.core.transaction_cache import transaction_cache


def test_asyncio_transactions_default_with_task():

    @background_task(name='test_asyncio_transactions_default')
    @asyncio.coroutine
    def coro():
        current = current_transaction()
        assert list(transaction_cache().asyncio_transactions()) == [current]
        yield from asyncio.sleep(0)
        current = current_transaction()
        assert list(transaction_cache().asyncio_transactions()) == [current]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(coro())


def test_asyncio_transactions_default_task_on_other_event_loop():

    @asyncio.coroutine
    @background_task(name='pause')
    def pause():
        pause_loop.stop()
        # Schedule a future on the IO loop after stop so this transaction
        # remains alive
        yield from asyncio.sleep(0.01)

    @asyncio.coroutine
    def coro():
        assert list(transaction_cache().asyncio_transactions()) == []
        yield from asyncio.sleep(0)
        assert list(transaction_cache().asyncio_transactions()) == []

    # Start a transaction on a different event loop
    pause_loop = asyncio.get_event_loop()
    pause_task = pause_loop.create_task(pause())
    pause_loop.run_forever()

    # The coroutine on this event loop does not have a transaction running
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro())

    # Fully consume the pause task
    asyncio.set_event_loop(pause_loop)
    pause_loop.run_until_complete(pause_task)


@background_task(name='test_asyncio_transactions_default_no_task')
def test_asyncio_transactions_default_no_task():
    assert list(transaction_cache().asyncio_transactions()) == []


def test_asyncio_transactions_different_loop_id():

    @background_task(name='test_asyncio_transactions_different_loop_id')
    @asyncio.coroutine
    def coro():
        assert list(transaction_cache().asyncio_transactions(id(None))) == []
        yield from asyncio.sleep(0)
        assert list(transaction_cache().asyncio_transactions(id(None))) == []

    loop = asyncio.get_event_loop()
    loop.run_until_complete(coro())
