import asyncio
import pytest
import sys
import aiohttp
from aiohttp import web
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        override_generic_settings, override_ignore_status_codes)


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


@asyncio.coroutine
def coro_for_test(close_exception=None):
    while True:
        try:
            yield
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
    (UncaughtException, UncaughtException),
    (web.HTTPGone, web.HTTPGone),
    (web.HTTPNotFound, web.HTTPNotFound),
])
def test_throw(injected, raises, nr_enabled):
    from newrelic.hooks.framework_aiohttp import NRTransactionCoroutineWrapper

    @asyncio.coroutine
    def _test_driver():
        coro = coro_for_test()

        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro, FakeRequest())

        # Force to iterator type
        coro = iter(coro)

        # drive coro a bit
        next(coro)

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

    loop = asyncio.new_event_loop()

    def _test():
        if raises:
            with pytest.raises(raises):
                loop.run_until_complete(_test_driver())
        else:
            result = loop.run_until_complete(_test_driver())
            assert result

    if nr_enabled:
        ignored = False
        if hasattr(raises, 'status_code') and raises.status_code == 404:
            ignored = True

        metrics = [('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1)]
        if raises and not ignored:
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
    from newrelic.hooks.framework_aiohttp import NRTransactionCoroutineWrapper

    @asyncio.coroutine
    def _test_driver():
        coro = coro_for_test(close_exception)

        # wrap the coroutine
        coro = NRTransactionCoroutineWrapper(coro, FakeRequest())

        # drive coro a bit
        next(coro)

        # immediately close the coro
        if close_exception:
            try:
                coro.close()
            except close_exception:
                pass
        else:
            coro.close()

        return True

    loop = asyncio.new_event_loop()

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


if sys.version_info >= (3, 5):
    from _test_await import test_await # NOQA
