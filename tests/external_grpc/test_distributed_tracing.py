import pytest
from newrelic.api.application import application_instance
from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace

from testing_support.fixtures import (override_application_settings,
        validate_transaction_metrics)
from _test_common import (create_stub, create_request,
        wait_for_transaction_completion)


_test_matrix = ('method_name,streaming_request', (
    ('DoUnaryUnary', False),
    ('DoUnaryStream', False),
    ('DoStreamUnary', True),
    ('DoStreamStream', True)
))


@override_application_settings({'distributed_tracing.enabled': True})
@pytest.mark.parametrize(*_test_matrix)
def test_inbound_distributed_trace(mock_grpc_server, method_name,
        streaming_request):
    stub = create_stub(mock_grpc_server)
    request = create_request(streaming_request)

    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    @validate_transaction_metrics(
        'sample_application:SampleApplicationServicer.' + method_name,
        rollup_metrics=(
            ('Supportability/DistributedTrace/AcceptPayload/Success', 1),
        ),
    )
    @wait_for_transaction_completion
    def _test():
        method = getattr(stub, method_name)
        response = method(request, metadata=dt_headers)

        try:
            list(response)
        except Exception:
            pass

    _test()
