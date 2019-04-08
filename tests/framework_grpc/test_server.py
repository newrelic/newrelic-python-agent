import grpc
import pytest
from _test_common import (create_stub, create_request,
    wait_for_transaction_completion)
from newrelic.core.config import global_settings
from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_event_attributes, override_application_settings,
        override_generic_settings, function_not_called)


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


@pytest.mark.parametrize(*_test_matrix)
def test_raises_response_status(method_name, streaming_request,
        mock_grpc_server):
    port = mock_grpc_server
    stub = create_stub(port)
    request = create_request(streaming_request)

    method_name = method_name + 'Raises'

    _transaction_name = \
        "sample_application:SampleApplicationServicer.{}".format(method_name)
    method = getattr(stub, method_name)

    status_code = str(grpc.StatusCode.UNKNOWN.value[0])

    @validate_transaction_metrics(_transaction_name)
    @override_application_settings({'attributes.include': ['request.*']})
    @validate_transaction_event_attributes(
            required_params={
                'agent': ['request.uri', 'request.headers.userAgent',
                    'response.status'],
                'user': [],
                'intrinsic': ['port'],
            },
            exact_attrs={
                'agent': {'response.status': status_code},
                'user': {},
                'intrinsic': {'port': port}
            })
    @wait_for_transaction_completion
    def _doit():
        try:
            response = method(request)
            list(response)
        except Exception:
            pass

    _doit()


def test_newrelic_disabled_no_transaction(mock_grpc_server):
    port = mock_grpc_server
    stub = create_stub(port)
    request = create_request(False)

    method = getattr(stub, 'DoUnaryUnary')

    @override_generic_settings(global_settings(), {'enabled': False})
    @function_not_called('newrelic.core.stats_engine',
        'StatsEngine.record_transaction')
    @wait_for_transaction_completion
    def _doit():
        method(request)

    _doit()
