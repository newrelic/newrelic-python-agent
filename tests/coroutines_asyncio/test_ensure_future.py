import sys
import pytest

from newrelic.api.background_task import background_task
from newrelic.api.function_trace import function_trace
from newrelic.api.transaction import current_transaction

from testing_support.fixtures import capture_transaction_metrics


@pytest.fixture()
def future_arg(request):
    # Avoid importing asyncio until after the instrumentation hooks are set up
    import asyncio

    loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def _coro(txn):
        try:
            assert current_transaction() is txn
            yield
            assert current_transaction() is txn
        finally:
            loop.stop()

    arg_type = request.getfixturevalue('arg_type')

    if arg_type == 'future':
        future = asyncio.Future()
        future.add_done_callback(lambda f: loop.stop())
        future.set_result(True)
        return lambda txn: future
    elif arg_type == 'coroutine':
        return _coro
    elif arg_type == 'awaitable':
        from _async_coroutine import awaitable
        return awaitable
    else:
        raise ValueError('Unrecognized argument type for ensure_future')


arg_types = ['future', 'coroutine']
if sys.version_info >= (3, 5):
    arg_types.append('awaitable')


@pytest.mark.parametrize('arg_type', arg_types)
@pytest.mark.parametrize('explicit_loop', [True, False])
@pytest.mark.parametrize('in_transaction', [True, False])
def test_ensure_future(explicit_loop, arg_type, future_arg, in_transaction):
    def _test():
        # Avoid importing asyncio until after the instrumentation hooks are set
        # up
        import asyncio
        if hasattr(asyncio, 'ensure_future'):
            ensure_future = asyncio.ensure_future
        else:
            # use getattr because `async` is a keyword in py37
            ensure_future = getattr(asyncio, 'async')

        loop = asyncio.get_event_loop()

        @asyncio.coroutine
        def timeout():
            yield from asyncio.sleep(2.0)
            loop.stop()
            raise TimeoutError("Test timed out")

        timeout_future = ensure_future(timeout())

        kwargs = {}
        if explicit_loop:
            kwargs['loop'] = loop

        txn = current_transaction()

        # Call ensure future prior to dropping the transaction
        task = ensure_future(future_arg(txn), **kwargs)

        # Drop the transaction explicitly.
        if in_transaction:
            txn.drop_transaction()

        try:
            loop = asyncio.get_event_loop()

            # This should run the coroutine until it calls stop
            loop.run_forever()

            # Cancel the timeout
            timeout_future.cancel()

            # Cause any exception to be reraised here
            task.result()
        finally:
            # Put the transaction back prior to transaction __exit__
            # Since transaction __exit__ calls drop_transaction, the
            # transaction is expected to be in the transaction cache
            if in_transaction:
                txn.save_transaction()

    if in_transaction:
        background_task(name='test_ensure_future')(_test)()
    else:
        _test()


@pytest.mark.xfail(strict=True, reason="Parenting is not correct for async "
    "code at the moment and therefore exclusive time is not calculated "
    "correctly.")
def test_exclusive_time():

    full_metrics = {}

    @capture_transaction_metrics([], full_metrics)
    @background_task(name='test_exclusive_time')
    def _test():
        # Avoid importing asyncio until after the instrumentation hooks are set
        # up
        import asyncio
        if hasattr(asyncio, 'ensure_future'):
            ensure_future = asyncio.ensure_future
        else:
            # use getattr because `async` is a keyword in py37
            ensure_future = getattr(asyncio, 'async')

        @asyncio.coroutine
        @function_trace(name='_coro')
        def _coro():
            yield from asyncio.sleep(0.1)

        @asyncio.coroutine
        def middle():
            yield from ensure_future(_coro())

        @asyncio.coroutine
        @function_trace(name='main')
        def main():
            yield from ensure_future(middle())

        asyncio.get_event_loop().run_until_complete(main())

    _test()

    coro_metric = ('Function/_coro', '')
    main_metric = ('Function/main', '')

    coro_exclusive_time = full_metrics[coro_metric][2]
    main_exclusive_time = full_metrics[main_metric][2]

    assert main_exclusive_time < coro_exclusive_time


@background_task(name='test_parent_trace_is_exited')
def test_parent_trace_is_exited():
    # Avoid importing asyncio until after the instrumentation hooks are set
    # up
    import asyncio
    if hasattr(asyncio, 'ensure_future'):
        ensure_future = asyncio.ensure_future
    else:
        # use getattr because `async` is a keyword in py37
        ensure_future = getattr(asyncio, 'async')

    futures = []
    loop = asyncio.get_event_loop()

    @asyncio.coroutine
    @function_trace(name='parent')
    def parent():
        f = ensure_future(middle())
        futures.append(f)

    @asyncio.coroutine
    def middle():
        yield
        yield from child()

    @asyncio.coroutine
    @function_trace(name='child')
    def child():
        yield
        loop.stop()

    @asyncio.coroutine
    def timeout():
        yield from asyncio.sleep(1)
        loop.stop()
        assert False

    loop.run_until_complete(parent())
    task = ensure_future(timeout())

    loop.run_forever()

    # Cancel timeout task - assertion will fire below if future did not
    # complete
    if not task.done():
        task.cancel()

    # Check that the future is complete
    assert futures[0].done()

    # Trigger an error if there is one
    futures[0].result()
