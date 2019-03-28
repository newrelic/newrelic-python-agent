import pytest
from _test_common import create_stub, create_request
from testing_support.fixtures import validate_transaction_metrics


_test_matrix = ["method_name,streaming_request", [
    ("DoUnaryUnary", False),
    ("DoUnaryStream", False),
    ("DoStreamUnary", True),
    ("DoStreamStream", True)
]]


@pytest.mark.parametrize(*_test_matrix)
def test_simple(method_name, streaming_request, mock_grpc_server):
    stub = create_stub(mock_grpc_server)
    request = create_request(streaming_request)
    _transaction_name = \
        "sample_application:SampleApplicationServicer.{}".format(method_name)
    method = getattr(stub, method_name)

    @validate_transaction_metrics(_transaction_name)
    def _doit():
        response = method(request)

        try:
            list(response)
        except Exception:
            pass

    _doit()
