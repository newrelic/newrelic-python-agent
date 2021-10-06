# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import asyncio
import aiohttp
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, validate_transaction_event_attributes,
        count_transactions, override_generic_settings,
        override_application_settings, override_ignore_status_codes)
version_info = tuple(int(_) for _ in aiohttp.__version__.split('.')[:2])


BASE_REQUIRED_ATTRS = ['request.headers.contentType',
            'request.method']

# The agent should not record these attributes in events unless the settings
# explicitly say to do so
BASE_FORGONE_ATTRS = ['request.parameters.hello']


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
                uri, headers={'content-type': 'text/plain'})
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
        @override_ignore_status_codes([404])
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
    ('/class?hello=world', '_target_application:HelloWorldView._respond'),
    ('/known_error?hello=world',
            '_target_application:KnownErrorView._respond'),
])
def test_simultaneous_requests(method, uri, metric_name,
        nr_enabled, aiohttp_app):

    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request(method, uri,
                headers={'content-type': 'text/plain'})
        assert resp.status == 200
        text = yield from resp.text()
        assert "Hello Aiohttp!" in text
        return resp

    @asyncio.coroutine
    def multi_fetch(loop):
        coros = [fetch() for i in range(2)]

        try:
            combined = asyncio.gather(*coros)
        except TypeError:
            combined = asyncio.gather(*coros, loop=loop)

        responses = yield from combined
        return responses

    required_attrs = list(BASE_REQUIRED_ATTRS)
    extra_required = list(BASE_FORGONE_ATTRS)

    required_attrs.extend(extra_required)

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


@pytest.mark.parametrize('nr_enabled', [True, False])
def test_system_response_creates_no_transaction(nr_enabled, aiohttp_app):
    @asyncio.coroutine
    def fetch():
        resp = yield from aiohttp_app.client.request('GET', '/404')
        assert resp.status == 404
        return resp

    if nr_enabled:
        transactions = []

        @count_transactions(transactions)
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())
            assert len(transactions) == 0
    else:
        settings = global_settings()

        @override_generic_settings(settings, {'enabled': False})
        def _test():
            aiohttp_app.loop.run_until_complete(fetch())

    _test()


def test_aborted_connection_creates_transaction(aiohttp_app):
    @asyncio.coroutine
    def fetch():
        try:
            yield from aiohttp_app.client.request('GET', '/hang', timeout=0.1)
        except asyncio.TimeoutError:
            try:
                # Force the client to disconnect (while the server is hanging)
                yield from aiohttp_app.client.close()
            # In aiohttp 1.X, this can result in a CancelledError being raised
            except asyncio.CancelledError:
                pass
            yield
            return

        assert False, "Request did not time out"

    transactions = []

    @count_transactions(transactions)
    def _test():
        aiohttp_app.loop.run_until_complete(fetch())
        assert len(transactions) == 1

    _test()


def test_work_after_request_not_recorded(aiohttp_app):
    resp = aiohttp_app.loop.run_until_complete(
            aiohttp_app.client.request('GET', '/background'))
    assert resp.status == 200

    @asyncio.coroutine
    def timeout():
        yield from asyncio.sleep(1)
        aiohttp_app.loop.stop()
        assert False

    task = aiohttp_app.loop.create_task(timeout())
    aiohttp_app.loop.run_forever()

    # Check that the timeout didn't fire
    assert not task.done()
    task.cancel()
