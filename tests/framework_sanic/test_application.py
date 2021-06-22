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
import sanic

from newrelic.core.config import global_settings
from collections import deque

from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace

from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings, validate_transaction_errors,
    validate_transaction_event_attributes,
    override_ignore_status_codes, override_generic_settings,
    function_not_called)


sanic_21 = int(sanic.__version__.split('.', 1)[0]) >= 21


BASE_METRICS = [
    ('Function/_target_application:index', 1),
    ('Function/_target_application:request_middleware', 1 if int(sanic.__version__.split('.', 1)[0]) > 18 else 2),
]
FRAMEWORK_METRICS = [
    ('Python/Framework/Sanic/%s' % sanic.__version__, 1),
]
BASE_ATTRS = ['response.status', 'response.headers.contentType',
        'response.headers.contentLength']

validate_base_transaction_event_attr = validate_transaction_event_attributes(
    required_params={'agent': BASE_ATTRS, 'user': [], 'intrinsic': []},
)


@validate_transaction_metrics(
    '_target_application:index',
    scoped_metrics=BASE_METRICS,
    rollup_metrics=BASE_METRICS + FRAMEWORK_METRICS,
)
@validate_base_transaction_event_attr
def test_simple_request(app):
    response = app.fetch('get', '/')
    assert response.status == 200


@function_not_called('newrelic.core.stats_engine',
        'StatsEngine.record_transaction')
def test_websocket(app):
    headers = {'upgrade': 'WebSocket'}
    response = app.fetch('get', '/', headers=headers)
    assert response.status == 200


@pytest.mark.parametrize('method', (
    'get',
    'post',
    'put',
    'patch',
    'delete',
))
def test_method_view(app, method):
    metric_name = 'Function/_target_application:MethodView.' + method

    @validate_transaction_metrics(
        '_target_application:MethodView.' + method,
        scoped_metrics=[(metric_name, 1)],
        rollup_metrics=[(metric_name, 1)],
    )
    @validate_base_transaction_event_attr
    def _test():
        response = app.fetch(method, '/method_view')
        assert response.status == 200

    _test()


DT_METRICS = [
    ('Supportability/DistributedTrace/AcceptPayload/Success', None),
    ('Supportability/TraceContext/TraceParent/Accept/Success', 1),
]


@validate_transaction_metrics(
    '_target_application:index',
    scoped_metrics=BASE_METRICS,
    rollup_metrics=BASE_METRICS + DT_METRICS + FRAMEWORK_METRICS,
)
@validate_base_transaction_event_attr
@override_application_settings({
    'distributed_tracing.enabled': True,
})
def test_inbound_distributed_trace(app):
    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    response = app.fetch('get', '/', headers=dict(dt_headers))
    assert response.status == 200

_params = ["error"]
if not sanic_21:
    _params.append('write_response_error')
@pytest.mark.parametrize('endpoint', _params)
def test_recorded_error(app, endpoint):
    ERROR_METRICS = [
        ('Function/_target_application:%s' % endpoint, 1),
    ]

    @validate_transaction_errors(errors=['builtins:ValueError'])
    @validate_base_transaction_event_attr
    @validate_transaction_metrics(
        '_target_application:%s' % endpoint,
        scoped_metrics=ERROR_METRICS,
        rollup_metrics=ERROR_METRICS + FRAMEWORK_METRICS,
    )
    def _test():
        if endpoint == 'write_response_error':
            with pytest.raises(ValueError):
                response = app.fetch('get', '/' + endpoint)
        else:
            response = app.fetch('get', '/' + endpoint)
            assert response.status == 500

    _test()


NOT_FOUND_METRICS = [
    ('Function/_target_application:not_found', 1),
]


@validate_transaction_metrics(
    '_target_application:not_found',
    scoped_metrics=NOT_FOUND_METRICS,
    rollup_metrics=NOT_FOUND_METRICS + FRAMEWORK_METRICS,
)
@validate_base_transaction_event_attr
@override_ignore_status_codes([404])
@validate_transaction_errors(errors=[])
def test_ignored_by_status_error(app):
    response = app.fetch('get', '/404')
    assert response.status == 404


DOUBLE_ERROR_METRICS = [
    ('Function/_target_application:zero_division_error', 1),
]


@validate_transaction_metrics(
    '_target_application:zero_division_error',
    scoped_metrics=DOUBLE_ERROR_METRICS,
    rollup_metrics=DOUBLE_ERROR_METRICS,
)
@validate_transaction_errors(
        errors=['builtins:ValueError', 'builtins:ZeroDivisionError'])
def test_error_raised_in_error_handler(app):
    # Because of a bug in Sanic versions <0.8.0, the response.status value is
    # inconsistent. Rather than assert the status value, we rely on the
    # transaction errors validator to confirm the application acted as we'd
    # expect it to.
    app.fetch('get', '/zero')


STREAMING_ATTRS = ['response.status', 'response.headers.contentType']
STREAMING_METRICS = [
    ('Function/_target_application:streaming', 1),
]


@validate_transaction_metrics(
    '_target_application:streaming',
    scoped_metrics=STREAMING_METRICS,
    rollup_metrics=STREAMING_METRICS,
)
@validate_transaction_event_attributes(
    required_params={'agent': STREAMING_ATTRS, 'user': [], 'intrinsic': []},
)
def test_streaming_response(app):
    # streaming responses do not have content-length headers
    response = app.fetch('get', '/streaming')
    assert response.status == 200


ERROR_IN_ERROR_TESTS = [
    ('/sync-error', '_target_application:sync_error',
        [('Function/_target_application:sync_error', 1),
            ('Function/_target_application:handle_custom_exception_sync', 1)],
        ['_target_application:CustomExceptionSync',
        'sanic.exceptions:SanicException']),

    ('/async-error', '_target_application:async_error',
        [('Function/_target_application:async_error', 1),
            ('Function/_target_application:handle_custom_exception_async', 1)],
        ['_target_application:CustomExceptionAsync']),
]


@pytest.mark.parametrize('url,metric_name,metrics,errors',
        ERROR_IN_ERROR_TESTS)
@pytest.mark.parametrize('nr_enabled', (True, False))
def test_errors_in_error_handlers(
        nr_enabled, app, url, metric_name, metrics, errors):
    settings = global_settings()

    @override_generic_settings(settings, {'enabled': nr_enabled})
    def _test():
        # Because of a bug in Sanic versions <0.8.0, the response.status value
        # is inconsistent. Rather than assert the status value, we rely on the
        # transaction errors validator to confirm the application acted as we'd
        # expect it to.
        app.fetch('get', url)

    if nr_enabled:
        _test = validate_transaction_errors(errors=errors)(_test)
        _test = validate_transaction_metrics(metric_name,
                scoped_metrics=metrics,
                rollup_metrics=metrics)(_test)
    else:
        _test = function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')(_test)

    _test()


def test_no_transaction_when_nr_disabled(app):
    settings = global_settings()

    @function_not_called('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    @override_generic_settings(settings, {'enabled': False})
    def _test():
        app.fetch('GET', '/')

    _test()


async def async_returning_middleware(*args, **kwargs):
    from sanic.response import json
    return json({'oops': 'I returned it again'})


def sync_returning_middleware(*args, **kwargs):
    from sanic.response import json
    return json({'oops': 'I returned it again'})


def sync_failing_middleware(*args, **kwargs):
    from sanic.exceptions import SanicException
    raise SanicException('Everything is ok', status_code=200)


@pytest.mark.parametrize('middleware,attach_to,metric_name,transaction_name', [
    (async_returning_middleware, 'request',
        'test_application:async_returning_middleware',
        'test_application:async_returning_middleware'),
    (sync_returning_middleware, 'request',
        'test_application:sync_returning_middleware',
        'test_application:sync_returning_middleware'),
    (sync_failing_middleware, 'request',
        'test_application:sync_failing_middleware',
        'test_application:sync_failing_middleware'),
    (async_returning_middleware, 'response',
        'test_application:async_returning_middleware',
        '_target_application:index'),
    (sync_returning_middleware, 'response',
        'test_application:sync_returning_middleware',
        '_target_application:index'),
])
def test_returning_middleware(app, middleware, attach_to, metric_name,
        transaction_name):

    metrics = [
        ('Function/%s' % metric_name, 1),
    ]

    @validate_transaction_metrics(
            transaction_name,
            scoped_metrics=metrics,
            rollup_metrics=metrics,
    )
    @validate_base_transaction_event_attr
    def _test():
        response = app.fetch('get', '/')
        assert response.status == 200

    original_request_middleware = deque(app.app.request_middleware)
    original_response_middleware = deque(app.app.response_middleware)
    app.app.register_middleware(middleware, attach_to)

    try:
        _test()
    finally:
        app.app.request_middleware = original_request_middleware
        app.app.response_middleware = original_response_middleware


def error_middleware(*args, **kwargs):
    raise ValueError("1 != 0")


def test_errors_in_middleware(app):
    metrics = [('Function/test_application:error_middleware', 1)]

    @validate_transaction_metrics(
            'test_application:error_middleware',
            scoped_metrics=metrics,
            rollup_metrics=metrics,
    )
    @validate_base_transaction_event_attr
    @validate_transaction_errors(errors=['builtins:ValueError'])
    def _test():
        response = app.fetch('get', '/')
        assert response.status == 500

    original_request_middleware = deque(app.app.request_middleware)
    original_response_middleware = deque(app.app.response_middleware)
    app.app.register_middleware(error_middleware, "request")

    try:
        _test()
    finally:
        app.app.request_middleware = original_request_middleware
        app.app.response_middleware = original_response_middleware


BLUEPRINT_METRICS = [
    ("Function/_target_application:blueprint_middleware", 1),
    ("Function/_target_application:blueprint_route", 1),
]


@validate_transaction_metrics(
    "_target_application:blueprint_route",
    scoped_metrics=BLUEPRINT_METRICS,
    rollup_metrics=BLUEPRINT_METRICS + FRAMEWORK_METRICS,
)
@validate_transaction_errors(errors=[])
def test_blueprint_middleware(app):
    response = app.fetch('get', '/blueprint')
    assert response.status == 200


def test_unknown_route(app):
    import sanic
    sanic_version = [int(x) for x in sanic.__version__.split(".")]
    _tx_name = "_target_application:CustomRouter.get" if sanic_version[0] < 21 else "_target_application:request_middleware"
    
    @validate_transaction_metrics(_tx_name)
    def _test():
        response = app.fetch('get', '/what-route')
        assert response.status == 404
    
    _test()    

def test_bad_method(app):
    import sanic
    sanic_version = [int(x) for x in sanic.__version__.split(".")]
    _tx_name = "_target_application:CustomRouter.get" if sanic_version[0] < 21 else "_target_application:request_middleware"

    @validate_transaction_metrics(_tx_name)
    @override_ignore_status_codes([405])
    @validate_transaction_errors(errors=[])
    def _test():
        response = app.fetch('post', '/')
        assert response.status == 405
    _test()