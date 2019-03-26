import pytest
import grpc
from testing_support.fixtures import validate_transaction_metrics

@pytest.fixture(scope='module')
def mock_grpc_server(grpc_app_server):
    from sample_application.sample_application_pb2_grpc import (
            add_SampleApplicationServicer_to_server)
    from sample_application import SampleApplicationServicer
    server, port = grpc_app_server
    add_SampleApplicationServicer_to_server(
            SampleApplicationServicer(), server)
    return port


def _create_stub(port):
    from sample_application.sample_application_pb2_grpc import (
            SampleApplicationStub)
    channel = grpc.insecure_channel('localhost:%s' % port)
    stub = SampleApplicationStub(channel)
    return stub


def _create_request(streaming_request, count=1, timesout=False):
    from sample_application.sample_application_pb2 import Message

    def _message_stream():
        for i in range(count):
            yield Message(text='Hello World', count=count, timesout=timesout)

    if streaming_request:
        request = _message_stream()
    else:
        request = Message(text='Hello World', count=count, timesout=timesout)

    return request


@validate_transaction_metrics('sample_application:SampleApplicationServicer.DoUnaryUnary')
def test_simple(mock_grpc_server):
    stub = _create_stub(mock_grpc_server)
    request = _create_request(False)

    reply = stub.DoUnaryUnary(request)
