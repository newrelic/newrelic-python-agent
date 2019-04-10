import time

from sample_application_pb2 import Message
from sample_application_pb2_grpc import (
        SampleApplicationServicer as _SampleApplicationServicer)


class SampleApplicationServicer(_SampleApplicationServicer):

    def DoUnaryUnary(self, request, context):
        context.set_trailing_metadata([('content-type', 'text/plain')])
        if request.timesout:
            while context.is_active():
                time.sleep(0.1)
        return Message(text='unary_unary: %s' % request.text)

    def DoUnaryStream(self, request, context):
        context.set_trailing_metadata([('content-type', 'text/plain')])
        if request.timesout:
            while context.is_active():
                time.sleep(0.1)
        for i in range(request.count):
            yield Message(text='unary_stream: %s' % request.text)

    def DoStreamUnary(self, request_iter, context):
        context.set_trailing_metadata([('content-type', 'text/plain')])
        for request in request_iter:
            if request.timesout:
                while context.is_active():
                    time.sleep(0.1)
            return Message(text='stream_unary: %s' % request.text)

    def DoStreamStream(self, request_iter, context):
        context.set_trailing_metadata([('content-type', 'text/plain')])
        for request in request_iter:
            if request.timesout:
                while context.is_active():
                    time.sleep(0.1)
            yield Message(text='stream_stream: %s' % request.text)

    def DoUnaryUnaryRaises(self, request, context):
        raise AssertionError('unary_unary: %s' % request.text)

    def DoUnaryStreamRaises(self, request, context):
        raise AssertionError('unary_stream: %s' % request.text)

    def DoStreamUnaryRaises(self, request_iter, context):
        for request in request_iter:
            raise AssertionError('stream_unary: %s' % request.text)

    def DoStreamStreamRaises(self, request_iter, context):
        for request in request_iter:
            raise AssertionError('stream_stream: %s' % request.text)

    def extract_dt_value(self, metadata):
        for k, v in metadata:
            if k != 'newrelic':
                continue
            return Message(text='%s' % v)

        return Message(text='')

    def DtUnaryUnary(self, request, context):
        return self.extract_dt_value(context.invocation_metadata())

    def DtUnaryStream(self, request, context):
        yield self.extract_dt_value(context.invocation_metadata())

    def DtStreamUnary(self, request_iter, context):
        list(request_iter)  # consume iterator
        return self.extract_dt_value(context.invocation_metadata())

    def DtStreamStream(self, request_iter, context):
        for request in request_iter:
            yield self.extract_dt_value(context.invocation_metadata())
