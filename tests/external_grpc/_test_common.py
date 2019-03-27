import grpc

__all__ = ['create_stub', 'create_request']


def create_stub(port):
    from sample_application.sample_application_pb2_grpc import (
            SampleApplicationStub)
    channel = grpc.insecure_channel('localhost:%s' % port)
    stub = SampleApplicationStub(channel)
    return stub


def create_request(streaming_request, count=1, timesout=False):
    from sample_application.sample_application_pb2 import Message

    def _message_stream():
        for i in range(count):
            yield Message(text='Hello World', count=count, timesout=timesout)

    if streaming_request:
        request = _message_stream()
    else:
        request = Message(text='Hello World', count=count, timesout=timesout)

    return request
