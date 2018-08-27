from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace
from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)


BASE_METRICS = [
    ('Function/_target_application:index', 1),
]


@validate_transaction_metrics(
    '_target_application:index',
    scoped_metrics=BASE_METRICS,
    rollup_metrics=BASE_METRICS,
)
def test_simple_request(app):
    response = app.fetch('get', '/')
    assert response.status == 200


MISNAMED_BASE_METRICS = [
        ('Function/_target_application:misnamed', 1),
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
    rollup_metrics=BASE_METRICS + DT_METRICS,
)
@override_application_settings({
    'distributed_tracing.enabled': True,
})
def test_inbound_distributed_trace(app):
    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    response = app.fetch('get', '/', headers=dict(dt_headers))
    assert response.status == 200
