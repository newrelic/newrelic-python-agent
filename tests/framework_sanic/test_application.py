import sanic

from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace
from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings, validate_transaction_errors,
    override_ignore_status_codes)


BASE_METRICS = [
    ('Function/_target_application:index', 1),
    ('Function/_target_application:request_middleware', 2),
    ('Function/_target_application:misnamed_response_middleware', 1),
]
FRAMEWORK_METRICS = [
    ('Python/Framework/Sanic/%s' % sanic.__version__, 1),
]


@validate_transaction_metrics(
    '_target_application:index',
    scoped_metrics=BASE_METRICS,
    rollup_metrics=BASE_METRICS + FRAMEWORK_METRICS,
)
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
@override_ignore_status_codes([404])
@validate_transaction_errors(errors=[])
def test_ignored_by_status_error(app):
    response = app.fetch('get', '/404')
    assert response.status == 404
