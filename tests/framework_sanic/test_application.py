from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace
from testing_support.fixtures import (validate_transaction_metrics,
    override_application_settings)


@validate_transaction_metrics('', group='Uri')
def test_simple_request(app):
    response = app.fetch('get', '/')
    assert response.status == 200


DT_METRICS = [
    ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
]


@validate_transaction_metrics(
    '',
    group='Uri',
    rollup_metrics=DT_METRICS,
)
@override_application_settings({
    'distributed_tracing.enabled': True,
})
def test_inbound_distributed_trace(app):
    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    response = app.fetch('get', '/', headers=dict(dt_headers))
    assert response.status == 200
