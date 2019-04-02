import pytest
from _test_common import (create_stub, create_request,
    wait_for_transaction_completion)
from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_event_attributes, override_application_settings)


_test_matrix = ["method_name,streaming_request", [
    ("DoUnaryUnary", False),
    ("DoUnaryStream", False),
    ("DoStreamUnary", True),
    ("DoStreamStream", True)
]]


@pytest.mark.parametrize(*_test_matrix)
def test_simple(method_name, streaming_request, mock_grpc_server):
    port = mock_grpc_server
    stub = create_stub(port)
    request = create_request(streaming_request)
    _transaction_name = \
        "sample_application:SampleApplicationServicer.{}".format(method_name)
    method = getattr(stub, method_name)

    @validate_transaction_metrics(_transaction_name)
    @override_application_settings({'attributes.include': ['request.*']})
    @validate_transaction_event_attributes(
            required_params={
                'agent': ['request.uri', 'request.headers.userAgent',
                    'response.status', 'response.headers.contentType'],
                'user': [],
                'intrinsic': ['port'],
            },
            exact_attrs={
                'agent': {},
                'user': {},
                'intrinsic': {'port': port}
            })
    @wait_for_transaction_completion
    def _doit():
        response = method(request)

        try:
            list(response)
        except Exception:
            pass

    _doit()
