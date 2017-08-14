import grpc
import random
import six

from newrelic.api.background_task import background_task

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors)
from testing_support.mock_external_grpc_server import MockExternalgRPCServer

from sample_application.sample_application_pb2_grpc import (
    add_SampleApplicationServicer_to_server, SampleApplicationStub)
from sample_application.sample_application_pb2 import Message
from sample_application import SampleApplicationServicer

PORT = random.randint(50000, 50100)


def _message_stream():
    yield Message(text='Hello World')


# UNARY UNARY

_test_unary_unary_scoped_metrics = [
        ('External/localhost:%s/gRPC/unary_unary' % PORT, None),
]

_test_unary_unary_rollup_metrics = [
        ('External/localhost:%s/gRPC/unary_unary' % PORT, None),
        ('External/localhost:%s/all' % PORT, None),
        ('External/allOther', None),
        ('External/all', None),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('test_blocking_clients:test_unary_unary__call__',
        scoped_metrics=_test_unary_unary_scoped_metrics,
        rollup_metrics=_test_unary_unary_rollup_metrics,
        background_task=True)
@background_task()
def test_unary_unary__call__():
    with MockExternalgRPCServer(port=PORT) as server:
        add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
                server)

        channel = grpc.insecure_channel('localhost:%s' % PORT)
        stub = SampleApplicationStub(channel)
        reply = stub.DoUnaryUnary(Message(text='Hello World'))
        assert reply.text == 'unary_unary: Hello World'


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_blocking_clients:test_unary_unary_with_call',
        scoped_metrics=_test_unary_unary_scoped_metrics,
        rollup_metrics=_test_unary_unary_rollup_metrics,
        background_task=True)
@background_task()
def test_unary_unary_with_call():
    with MockExternalgRPCServer(port=PORT) as server:
        add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
                server)

        channel = grpc.insecure_channel('localhost:%s' % PORT)
        stub = SampleApplicationStub(channel)
        reply, rendezvous = stub.DoUnaryUnary.with_call(
                Message(text='Hello World'))
        assert reply.text == 'unary_unary: Hello World'
        assert rendezvous.code() == grpc.StatusCode.OK


if six.PY2:
    _test_unary_unary_raises_transaction_name = (
            'test_blocking_clients:_test_unary_unary')
else:
    _test_unary_unary_raises_transaction_name = (
            'test_blocking_clients:'
            'test_unary_unary__call__raises.<locals>._test_unary_unary')


@validate_transaction_errors(errors=['grpc._channel:_Rendezvous'])
@validate_transaction_metrics(_test_unary_unary_raises_transaction_name,
        scoped_metrics=_test_unary_unary_scoped_metrics,
        rollup_metrics=_test_unary_unary_rollup_metrics,
        background_task=True)
def test_unary_unary__call__raises():

    @background_task()
    def _test_unary_unary():
        with MockExternalgRPCServer(port=PORT) as server:
            add_SampleApplicationServicer_to_server(
                    SampleApplicationServicer(), server)

            channel = grpc.insecure_channel('localhost:%s' % PORT)
            stub = SampleApplicationStub(channel)
            stub.DoUnaryUnaryRaises(Message(text='Hello World'))

    try:
        _test_unary_unary()
    except grpc.RpcError as e:
        assert 'unary_unary: Hello World' in e.details()


if six.PY2:
    _test_unary_unary_raises_transaction_name = (
            'test_blocking_clients:_test_unary_unary')
else:
    _test_unary_unary_raises_transaction_name = (
            'test_blocking_clients:'
            'test_unary_unary_with_call_raises.<locals>._test_unary_unary')


@validate_transaction_errors(errors=['grpc._channel:_Rendezvous'])
@validate_transaction_metrics(_test_unary_unary_raises_transaction_name,
        scoped_metrics=_test_unary_unary_scoped_metrics,
        rollup_metrics=_test_unary_unary_rollup_metrics,
        background_task=True)
def test_unary_unary_with_call_raises():

    @background_task()
    def _test_unary_unary():
        with MockExternalgRPCServer(port=PORT) as server:
            add_SampleApplicationServicer_to_server(
                    SampleApplicationServicer(), server)

            channel = grpc.insecure_channel('localhost:%s' % PORT)
            stub = SampleApplicationStub(channel)
            stub.DoUnaryUnaryRaises.with_call(Message(text='Hello World'))

    try:
        _test_unary_unary()
    except grpc.RpcError:
        pass  # this error is expected


# STREAM UNARY

_test_stream_unary_scoped_metrics = [
        ('External/localhost:%s/gRPC/stream_unary' % PORT, None),
]

_test_stream_unary_rollup_metrics = [
        ('External/localhost:%s/gRPC/stream_unary' % PORT, None),
        ('External/localhost:%s/all' % PORT, None),
        ('External/allOther', None),
        ('External/all', None),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_blocking_clients:test_stream_unary__call__',
        scoped_metrics=_test_stream_unary_scoped_metrics,
        rollup_metrics=_test_stream_unary_rollup_metrics,
        background_task=True)
@background_task()
def test_stream_unary__call__():
    with MockExternalgRPCServer(port=PORT) as server:
        add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
                server)

        channel = grpc.insecure_channel('localhost:%s' % PORT)
        stub = SampleApplicationStub(channel)
        reply = stub.DoStreamUnary(_message_stream())
        assert reply.text == 'stream_unary: Hello World'


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_blocking_clients:test_stream_unary_with_call',
        scoped_metrics=_test_stream_unary_scoped_metrics,
        rollup_metrics=_test_stream_unary_rollup_metrics,
        background_task=True)
@background_task()
def test_stream_unary_with_call():
    with MockExternalgRPCServer(port=PORT) as server:
        add_SampleApplicationServicer_to_server(SampleApplicationServicer(),
                server)

        channel = grpc.insecure_channel('localhost:%s' % PORT)
        stub = SampleApplicationStub(channel)
        reply, rendezvous = stub.DoStreamUnary.with_call(_message_stream())
        assert reply.text == 'stream_unary: Hello World'
        assert rendezvous.done()


if six.PY2:
    _test_stream_unary_raises_transaction_name = (
            'test_blocking_clients:_test_stream_unary')
else:
    _test_stream_unary_raises_transaction_name = (
            'test_blocking_clients:'
            'test_stream_unary__call__raises.<locals>._test_stream_unary')


@validate_transaction_errors(errors=['grpc._channel:_Rendezvous'])
@validate_transaction_metrics(_test_stream_unary_raises_transaction_name,
        scoped_metrics=_test_stream_unary_scoped_metrics,
        rollup_metrics=_test_stream_unary_rollup_metrics,
        background_task=True)
def test_stream_unary__call__raises():

    @background_task()
    def _test_stream_unary():
        with MockExternalgRPCServer(port=PORT) as server:
            add_SampleApplicationServicer_to_server(
                    SampleApplicationServicer(), server)

            channel = grpc.insecure_channel('localhost:%s' % PORT)
            stub = SampleApplicationStub(channel)
            stub.DoStreamUnaryRaises(_message_stream())

    try:
        _test_stream_unary()
    except grpc.RpcError:
        pass  # this error is expected


if six.PY2:
    _test_stream_unary_raises_transaction_name = (
            'test_blocking_clients:_test_stream_unary')
else:
    _test_stream_unary_raises_transaction_name = (
            'test_blocking_clients:'
            'test_stream_unary_with_call_raises.<locals>._test_stream_unary')


@validate_transaction_errors(errors=['grpc._channel:_Rendezvous'])
@validate_transaction_metrics(_test_stream_unary_raises_transaction_name,
        scoped_metrics=_test_stream_unary_scoped_metrics,
        rollup_metrics=_test_stream_unary_rollup_metrics,
        background_task=True)
def test_stream_unary_with_call_raises():

    @background_task()
    def _test_stream_unary():
        with MockExternalgRPCServer(port=PORT) as server:
            add_SampleApplicationServicer_to_server(
                    SampleApplicationServicer(), server)

            channel = grpc.insecure_channel('localhost:%s' % PORT)
            stub = SampleApplicationStub(channel)
            stub.DoStreamUnaryRaises.with_call(_message_stream())

    try:
        _test_stream_unary()
    except grpc.RpcError:
        pass  # this error is expected
