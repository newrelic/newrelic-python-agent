import pytest
import asyncio
import aiohttp
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, validate_transaction_event_attributes,
        count_transactions, override_generic_settings,
        override_application_settings)


BASE_REQUIRED_ATTRS = ['request.headers.contentType',
            'request.method']

# The agent should not record these attributes in events unless the settings
# explicitly say to do so
BASE_FORGONE_ATTRS = ['request.parameters.hello',
            'request.headers.accept', 'request.headers.host',
            'request.headers.userAgent']


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('method', [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
])
@pytest.mark.parametrize('uri,metric_name,error,status', [
    (
        '/error?hello=world',
        '_target_application:error',
        'builtins:ValueError',
        500
    ),

    (
        '/non_500_error?hello=world',
        '_target_application:non_500_error',
        'aiohttp.web_exceptions:HTTPGone',
        410
    ),

    (
        '/raise_404?hello=world',
        '_target_application:raise_404',
        None,
        404
    ),
])
def test_error_exception(method, uri, metric_name, error, status, nr_enabled,
        aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method,
                uri)
        assert resp.status == status

    required_attrs = list(BASE_REQUIRED_ATTRS)
    forgone_attrs = list(BASE_FORGONE_ATTRS)

    if nr_enabled:
        errors = []
        if error:
            errors.append(error)

        @validate_transaction_errors(errors=errors)
        @validate_transaction_metrics(metric_name,
            scoped_metrics=[
                ('Function/%s' % metric_name, 1),
            ],
            rollup_metrics=[
                ('Function/%s' % metric_name, 1),
                ('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1),
            ],
        )
        @validate_transaction_event_attributes(
            required_params={
                'agent': required_attrs,
                'user': [],
                'intrinsic': [],
            },
            forgone_params={
                'agent': forgone_attrs,
                'user': [],
                'intrinsic': [],
            },
            exact_attrs={
                'agent': {
                    'response.status': str(status),
                },
                'user': {},
                'intrinsic': {},
            },
        )
        @override_application_settings({
                'error_collector.ignore_status_codes': [404]})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())

    _test()


@pytest.mark.parametrize('nr_enabled', [True, False])
@pytest.mark.parametrize('method', [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
])
@pytest.mark.parametrize('uri,metric_name', [
    ('/coro?hello=world', '_target_application:index'),
    ('/class?hello=world', '_target_application:HelloWorldView'),
    ('/known_error?hello=world', '_target_application:KnownErrorView'),
])
def test_simultaneous_requests(method, uri, metric_name,
        nr_enabled, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method, uri)
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text
        return resp

    @asyncio.coroutine
    def multi_fetch(loop):
        coros = [fetch() for i in range(2)]
        combined = asyncio.gather(*coros, loop=loop)
        responses = yield from combined
        return responses

    required_attrs = list(BASE_REQUIRED_ATTRS)
    extra_required = list(BASE_FORGONE_ATTRS)

    required_attrs.extend(extra_required)

    required_attrs.extend(['response.status',
            'response.headers.contentType'])

    required_attrs.extend(['response.status',
            'response.headers.contentType'])

    if nr_enabled:
        transactions = []

        @override_application_settings({'attributes.include': ['request.*']})
        @validate_transaction_metrics(metric_name,
            scoped_metrics=[
                ('Function/%s' % metric_name, 1),
            ],
            rollup_metrics=[
                ('Function/%s' % metric_name, 1),
                ('Python/Framework/aiohttp/%s' % aiohttp.__version__, 1),
            ],
        )
        @validate_transaction_event_attributes(
            required_params={
                'agent': required_attrs,
                'user': [],
                'intrinsic': [],
            },
            forgone_params={
                'agent': [],
                'user': [],
                'intrinsic': [],
            },
        )
        @count_transactions(transactions)
        def _test():
            aiohttp_app.loop.run_until_complete(multi_fetch(aiohttp_app.loop))
            assert len(transactions) == 2
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(multi_fetch(aiohttp_app.loop))

    _test()
