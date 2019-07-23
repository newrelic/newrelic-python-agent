import pytest
import asyncio
import time
from newrelic.api.background_task import background_task
from testing_support.fixtures import validate_transaction_metrics


@background_task(name="block")
@asyncio.coroutine
def block_loop(ready, done, blocking_transaction_active):
    yield from ready.wait()
    time.sleep(0.1)
    done.set()
    if blocking_transaction_active:
        ready.clear()
        yield from ready.wait()


_wait_metrics_scoped = (
    ("IoLoop/Wait/OtherTransaction/Function/block", 1),
)
_wait_metrics_rollup = (
    ("IoLoop/Wait/all", 1),
    ("IoLoop/Wait/allOther", 1),
)


@background_task(name="wait")
@asyncio.coroutine
def wait_for_loop(ready, done):
    ready.set()
    yield from done.wait()
    ready.set()


@pytest.mark.parametrize('blocking_transaction_active', (True, False))
def test_record_io_loop_wait(blocking_transaction_active):
    import asyncio

    ready, done = (asyncio.Event(), asyncio.Event())
    future = asyncio.gather(
        wait_for_loop(ready, done),
        block_loop(ready, done, blocking_transaction_active),
    )

    index = 0 if blocking_transaction_active else -1

    @validate_transaction_metrics(
        "wait",
        scoped_metrics=_wait_metrics_scoped,
        rollup_metrics=_wait_metrics_rollup,
        background_task=True,
        index=index,
    )
    def _test():
        asyncio.get_event_loop().run_until_complete(future)

    _test()
