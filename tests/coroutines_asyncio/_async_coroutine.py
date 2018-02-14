import asyncio
from newrelic.api.transaction import current_transaction


async def awaitable():
    loop = asyncio.get_event_loop()
    try:
        assert current_transaction() is not None
        await asyncio.sleep(0)
        assert current_transaction() is not None
    finally:
        loop.stop()
