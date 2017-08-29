import grpc
import pytest
import six

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors)


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


_test_matrix = [
    ('service_method_type,service_method_method_name,raises_exception,'
    'message_count,cancel'), (
        ('unary_unary', '__call__', False, 1, False),
        ('unary_unary', '__call__', True, 1, False),
        ('unary_unary', 'with_call', False, 1, False),
        ('unary_unary', 'with_call', True, 1, False),
        ('unary_unary', 'future', False, 1, False),
        ('unary_unary', 'future', True, 1, False),
        ('unary_unary', 'future', False, 1, True),

        ('stream_unary', '__call__', False, 1, False),
        ('stream_unary', '__call__', True, 1, False),
        ('stream_unary', 'with_call', False, 1, False),
        ('stream_unary', 'with_call', True, 1, False),
        ('stream_unary', 'future', False, 1, False),
        ('stream_unary', 'future', True, 1, False),
        ('stream_unary', 'future', False, 1, True),

        ('unary_stream', '__call__', False, 1, False),
        ('unary_stream', '__call__', True, 1, False),
        ('unary_stream', '__call__', False, 2, False),
        ('unary_stream', '__call__', True, 2, False),
        ('unary_stream', '__call__', False, 1, True),
        ('unary_stream', '__call__', False, 2, True),

        ('stream_stream', '__call__', False, 1, False),
        ('stream_stream', '__call__', True, 1, False),
        ('stream_stream', '__call__', False, 2, False),
        ('stream_stream', '__call__', True, 2, False),
        ('stream_stream', '__call__', False, 1, True),
        ('stream_stream', '__call__', False, 2, True),
)]


@pytest.mark.parametrize(*_test_matrix)
def test_client(service_method_type, service_method_method_name,
        raises_exception, message_count, cancel, mock_grpc_server):

    port = mock_grpc_server

    service_method_class_name = 'Do%s%s' % (
            service_method_type.title().replace('_', ''),
            'Raises' if raises_exception else '')
    streaming_request = service_method_type.split('_')[0] == 'stream'
    streaming_response = service_method_type.split('_')[1] == 'stream'

    if cancel:
        # if cancelled, no communication happens over the wire
        expected_metrics_count = None
    elif not streaming_response or raises_exception:
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
    if raises_exception or cancel:
        _errors.append('grpc._channel:_Rendezvous')

    @validate_transaction_errors(errors=_errors)
    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=_test_scoped_metrics,
            rollup_metrics=_test_rollup_metrics,
            background_task=True)
    @background_task()
    def _test_client():
        stub = _create_stub(port)

        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = getattr(service_method_class,
                service_method_method_name)

        request = _create_request(streaming_request, count=message_count,
                timesout=False)

        reply = service_method_method(request)

        if isinstance(reply, tuple):
            reply = reply[0]

        if cancel:
            reply.cancel()

        try:
            # If the reply was canceled or the server code raises an exception,
            # this will raise an exception which will be recorded by the agent
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
        elif cancel:
            assert e.code() == grpc.StatusCode.CANCELLED
        else:
            raise


_test_matrix = [
    ('service_method_type,service_method_method_name,future_response'), (
        ('unary_unary', '__call__', False),
        ('unary_unary', 'with_call', False),
        ('unary_unary', 'future', True),

        ('stream_unary', '__call__', False),
        ('stream_unary', 'with_call', False),
        ('stream_unary', 'future', True),

        ('unary_stream', '__call__', True),

        ('stream_stream', '__call__', True),
)]


@pytest.mark.parametrize(*_test_matrix)
def test_bad_metadata(service_method_type, service_method_method_name,
        future_response, mock_grpc_server):
    port = mock_grpc_server

    service_method_class_name = 'Do%s' % (
            service_method_type.title().replace('_', ''))
    streaming_request = service_method_type.split('_')[0] == 'stream'

    _test_scoped_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type),
                None),
    ]
    _test_rollup_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type),
                None),
            ('External/localhost:%s/all' % port, None),
            ('External/allOther', None),
            ('External/all', None),
    ]

    if six.PY2:
        _test_transaction_name = 'test_clients:_test_bad_metadata'
    else:
        _test_transaction_name = (
                'test_clients:test_bad_metadata.<locals>._test_bad_metadata')

    if future_response:
        expected_exception = grpc.RpcError
    else:
        expected_exception = ValueError

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=_test_scoped_metrics,
            rollup_metrics=_test_rollup_metrics,
            background_task=True)
    @background_task()
    def _test_bad_metadata():
        stub = _create_stub(port)

        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = getattr(service_method_class,
                service_method_method_name)

        request = _create_request(streaming_request, count=1, timesout=False)

        with pytest.raises(expected_exception) as error:
            # gRPC doesn't like capital letters in metadata keys
            reply = service_method_method(request, metadata=[('ASDF', 'a')])
            reply.result()

        if future_response:
            assert error.value.code() == grpc.StatusCode.INTERNAL

    _test_bad_metadata()


@pytest.mark.parametrize(*_test_matrix)
def test_future_timeout_error(service_method_type, service_method_method_name,
        future_response, mock_grpc_server):
    port = mock_grpc_server

    service_method_class_name = 'Do%s' % (
            service_method_type.title().replace('_', ''))
    streaming_request = service_method_type.split('_')[0] == 'stream'

    _test_scoped_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type), 1),
    ]
    _test_rollup_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type), 1),
            ('External/localhost:%s/all' % port, 1),
            ('External/allOther', 1),
            ('External/all', 1),
    ]

    if six.PY2:
        _test_transaction_name = 'test_clients:_test_future_timeout_error'
    else:
        _test_transaction_name = (
                'test_clients:test_future_timeout_error.<locals>.'
                '_test_future_timeout_error')

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=_test_scoped_metrics,
            rollup_metrics=_test_rollup_metrics,
            background_task=True)
    @background_task()
    def _test_future_timeout_error():
        stub = _create_stub(port)

        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = getattr(service_method_class,
                service_method_method_name)

        request = _create_request(streaming_request, count=1, timesout=True)

        with pytest.raises(grpc.RpcError) as error:
            reply = service_method_method(request, timeout=0.01)
            list(reply)

        assert error.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED

    _test_future_timeout_error()


@pytest.mark.parametrize(*_test_matrix)
def test_server_down(service_method_type, service_method_method_name,
        future_response):
    port = 1234

    service_method_class_name = 'Do%s' % (
            service_method_type.title().replace('_', ''))
    streaming_request = service_method_type.split('_')[0] == 'stream'

    _test_scoped_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type), 1),
    ]
    _test_rollup_metrics = [
            ('External/localhost:%s/gRPC/%s' % (port, service_method_type), 1),
            ('External/localhost:%s/all' % port, 1),
            ('External/allOther', 1),
            ('External/all', 1),
    ]

    if six.PY2:
        _test_transaction_name = 'test_clients:_test_server_down'
    else:
        _test_transaction_name = (
                'test_clients:test_server_down.<locals>._test_server_down')

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=_test_scoped_metrics,
            rollup_metrics=_test_rollup_metrics,
            background_task=True)
    @background_task()
    def _test_server_down():
        stub = _create_stub(port)

        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = getattr(service_method_class,
                service_method_method_name)

        request = _create_request(streaming_request, count=1, timesout=False)

        with pytest.raises(grpc.RpcError) as error:
            reply = service_method_method(request)
            list(reply)

        assert error.value.code() == grpc.StatusCode.UNAVAILABLE

    _test_server_down()
