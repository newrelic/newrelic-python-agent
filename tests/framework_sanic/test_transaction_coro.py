import asyncio
import pytest
import sanic

from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings, override_ignore_status_codes,
        function_not_called)

from testing_support.validators.validate_ignored_transactions import \
    validate_ignored_transactions


class KnownException(Exception):
    pass


class ContinueException(Exception):
    pass


class UncaughtException(Exception):
    pass


class FakeRequest:
    path = '/coro_for_test'
    method = 'GET'
    headers = {}
    content_type = 'Foobar'
    query_string = ''


async def coro_for_test(close_exception=None, terminates=False):
    while True:
        try:
            await asyncio.sleep(0)
            if terminates:
                break
        except ContinueException:
            continue
        except KnownException:
            break
        except GeneratorExit:
            if close_exception is StopIteration:
                return True
            elif close_exception:
                raise close_exception()
            raise

    return True


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('injected,raises', [
    (KnownException, None),
    (UncaughtException, UncaughtException)
])
def test_throw(injected, raises, nr_enabled):
    from newrelic.hooks.framework_sanic import NRTransactionCoroutineWrapper

    async def _test_driver():
        coro = coro_for_test()

        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro, FakeRequest())

        # drive coro a bit
        coro.send(None)

        # this should cause the coro to continue
        try:
            coro.throw(ContinueException())
        except:
            # The coroutine stopped
            return False

        # this should cause a stop
        try:
            coro.throw(injected())
        except StopIteration as e:
            return e.value

        # the coroutine did not stop
        return False

    loop = asyncio.get_event_loop()

    def _test():
        if raises:
            with pytest.raises(raises):
                loop.run_until_complete(_test_driver())
        else:
            result = loop.run_until_complete(_test_driver())
            assert result

    if nr_enabled:
        metrics = [('Python/Framework/Sanic/%s' % sanic.__version__, 1)]
        if raises:
            metrics.append(('Errors/all', 1))
        else:
            metrics.append(('Errors/all', None))

        _test = validate_transaction_metrics(
                'coro_for_test', group='Uri',
                rollup_metrics=metrics)(_test)

        _test = override_ignore_status_codes([404])(_test)
    else:
        settings = global_settings()
        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()


@pytest.mark.parametrize('close_exception',
        [None, StopIteration, UncaughtException])
@pytest.mark.parametrize('nr_enabled', [True, False])
def test_close(nr_enabled, close_exception):
    from newrelic.hooks.framework_sanic import NRTransactionCoroutineWrapper

    async def _test_driver():
        coro = coro_for_test(close_exception)

        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro, FakeRequest())

        # drive coro a bit
        coro.send(None)

        # immediately close the coro
        if close_exception:
            try:
                coro.close()
            except close_exception:
                pass
        else:
            coro.close()

        return True

    loop = asyncio.get_event_loop()

    def _test():
        result = loop.run_until_complete(_test_driver())
        assert result

    if nr_enabled:
        _test = validate_transaction_metrics(
                'coro_for_test', group='Uri')(_test)
    else:
        settings = global_settings()
        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()


@pytest.mark.parametrize('ignored', [True, False])
def test_canceled(ignored):
    from newrelic.hooks.framework_sanic import NRTransactionCoroutineWrapper

    loop = asyncio.get_event_loop()

    async def _test_driver():
        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro_for_test(), FakeRequest())

        # create a task out of it, so we can cancel it later
        task = asyncio.Task(coro, loop=loop)

        # drive the coro so that a transaction will start
        coro.send(None)

        # now cancel; we should have bailed out of the current transaction
        if ignored:
            task.cancel()
        return True

    count = 1 if ignored else 0

    @function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    @validate_ignored_transactions(name='/coro_for_test', count=count)
    def _test():
        result = loop.run_until_complete(_test_driver())
        assert result

    _test()


@pytest.mark.parametrize('nr_enabled', (True, False))
def test_await(nr_enabled):
    from newrelic.hooks.framework_sanic import NRTransactionCoroutineWrapper

    async def _test_driver():
        coro = coro_for_test(terminates=True)

        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro, FakeRequest())

        return await coro

    loop = asyncio.get_event_loop()

    def _test():
        result = loop.run_until_complete(_test_driver())
        assert result

    if nr_enabled:
        _test = validate_transaction_metrics(
                'coro_for_test', group='Uri')(_test)
    else:
        settings = global_settings()
        _test = override_generic_settings(settings, {'enabled': False})(_test)

    _test()
