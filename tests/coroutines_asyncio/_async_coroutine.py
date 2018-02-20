import asyncio
from newrelic.api.transaction import current_transaction


async def awaitable(txn):
    loop = asyncio.get_event_loop()
    try:
        assert current_transaction() is txn
        await asyncio.sleep(0)
        assert current_transaction() is txn
    finally:
        loop.stop()
