import pytest
import sanic

from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_ignore_status_codes,
    validate_transaction_event_attributes, override_application_settings)


BASE_METRICS = [
    ('Function/_target_application:index', 1),
    ('Function/_target_application:request_middleware', 2),
    ('Function/_target_application:misnamed_response_middleware', 1),
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


MISNAMED_BASE_METRICS = [
    ('Function/_target_application:misnamed', 1),
    ('Function/_target_application:request_middleware', 2),
    ('Function/_target_application:misnamed_response_middleware', 1),
]


@validate_transaction_metrics(
    '_target_application:misnamed',
    scoped_metrics=MISNAMED_BASE_METRICS,
    rollup_metrics=MISNAMED_BASE_METRICS,
)
@validate_base_transaction_event_attr
def test_misnamed_handler(app):
    response = app.fetch('get', '/misnamed')
    assert response.status == 200


DT_METRICS = [
    ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
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


ERROR_METRICS = [
    ('Function/_target_application:error', 1),
]


@validate_transaction_metrics(
    '_target_application:error',
    scoped_metrics=ERROR_METRICS,
    rollup_metrics=ERROR_METRICS + FRAMEWORK_METRICS,
)
@validate_transaction_errors(errors=['builtins:ValueError'])
@validate_base_transaction_event_attr
def test_recorded_error(app):
    response = app.fetch('get', '/error')
    assert response.status == 500


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
        ['_target_application:CustomExceptionSync',
        'sanic.exceptions:SanicException']),
    ('/async-error', '_target_application:async_error',
        ['_target_application:CustomExceptionAsync']),
]


@pytest.mark.parametrize('url,metric_name,errors', ERROR_IN_ERROR_TESTS)
def test_errors_in_error_handlers(app, url, metric_name, errors):

    _metrics = [
            ('Function/%s' % metric_name, 1),
            # TODO: add in function traces for the error handlers
    ]

    @validate_transaction_metrics(metric_name,
            scoped_metrics=_metrics,
            rollup_metrics=_metrics)
    @validate_transaction_errors(errors=errors)
    def _test():
        # Because of a bug in Sanic versions <0.8.0, the response.status value
        # is inconsistent. Rather than assert the status value, we rely on the
        # transaction errors validator to confirm the application acted as we'd
        # expect it to.
        app.fetch('get', url)

    _test()
