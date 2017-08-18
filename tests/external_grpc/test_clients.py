import grpc
import pytest
import six

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors)

from sample_application.sample_application_pb2_grpc import (
        add_SampleApplicationServicer_to_server, SampleApplicationStub)
from sample_application.sample_application_pb2 import Message
from sample_application import SampleApplicationServicer


@pytest.fixture(scope='module')
def mock_grpc_server(grpc_app_server):
    server, port = grpc_app_server
    add_SampleApplicationServicer_to_server(
            SampleApplicationServicer(), server)
    return port


def _message_stream(count=1):
    for i in range(count):
        yield Message(text='Hello World', count=count)


_test_matrix = [
    ('service_method_type,service_method_method_name,raises_exception,'
    'message_count'), (
        ('unary_unary', '__call__', False, 1),
        ('unary_unary', '__call__', True, 1),
        ('unary_unary', 'with_call', False, 1),
        ('unary_unary', 'with_call', True, 1),
        ('unary_unary', 'future', False, 1),
        ('unary_unary', 'future', True, 1),

        ('stream_unary', '__call__', False, 1),
        ('stream_unary', '__call__', True, 1),
        ('stream_unary', 'with_call', False, 1),
        ('stream_unary', 'with_call', True, 1),
        ('stream_unary', 'future', False, 1),
        ('stream_unary', 'future', True, 1),

        ('unary_stream', '__call__', False, 1),
        ('unary_stream', '__call__', True, 1),
        pytest.param('unary_stream', '__call__', False, 2,
            marks=pytest.mark.xfail(reason='not implemented', strict=True)),
        ('unary_stream', '__call__', True, 2),

        ('stream_stream', '__call__', False, 1),
        ('stream_stream', '__call__', True, 1),
        pytest.param('stream_stream', '__call__', False, 2,
            marks=pytest.mark.xfail(reason='not implemented', strict=True)),
        ('stream_stream', '__call__', True, 2),
)]


@pytest.mark.parametrize(*_test_matrix)
def test_client(service_method_type, service_method_method_name,
        raises_exception, message_count, mock_grpc_server):

    port = mock_grpc_server

    service_method_class_name = 'Do%s%s' % (
            service_method_type.title().replace('_', ''),
            'Raises' if raises_exception else '')
    streaming_request = service_method_type.split('_')[0] == 'stream'
    streaming_response = service_method_type.split('_')[1] == 'stream'

    if not streaming_response or raises_exception:
        expected_metrics_count = 1
    else:
        expected_metrics_count = message_count

    _test_scoped_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type),
                expected_metrics_count),
    ]
    _test_rollup_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type),
                expected_metrics_count),
            ('External/localhost:%s/all' % port, expected_metrics_count),
            ('External/allOther', expected_metrics_count),
            ('External/all', expected_metrics_count),
    ]

    if six.PY2:
        _test_transaction_name = 'test_clients:_test_client'
    else:
        _test_transaction_name = (
                'test_clients:test_client.<locals>._test_client')

    _errors = []
    if raises_exception:
        _errors.append('grpc._channel:_Rendezvous')

    @validate_transaction_errors(errors=_errors)
    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=_test_scoped_metrics,
            rollup_metrics=_test_rollup_metrics,
            background_task=True)
    @background_task()
    def _test_client():
        channel = grpc.insecure_channel('localhost:%s' % port)
        stub = SampleApplicationStub(channel)

        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = getattr(service_method_class,
                service_method_method_name)

        if streaming_request:
            request = _message_stream(count=message_count)
        else:
            request = Message(text='Hello World', count=message_count)

        rendezvous = None
        reply = service_method_method(request)

        if isinstance(reply, tuple):
            reply, rendezvous = reply

        try:
            reply = list(reply)
        except TypeError:
            reply = [reply]

        expected_text = '%s: Hello World' % service_method_type
        response_texts_correct = [r.text == expected_text for r in reply]
        assert len(response_texts_correct) == message_count
        assert response_texts_correct and all(response_texts_correct)

    try:
        _test_client()
    except grpc.RpcError as e:
        if raises_exception:
            assert '%s: Hello World' % service_method_type in e.details()
        else:
            raise
