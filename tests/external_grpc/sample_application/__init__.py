import time

from sample_application_pb2 import Message
from sample_application_pb2_grpc import (
        SampleApplicationServicer as _SampleApplicationServicer)


class SampleApplicationServicer(_SampleApplicationServicer):

    def DoUnaryUnary(self, request, context):
        if request.timesout:
            while context.is_active():
                time.sleep(0.1)
        return Message(text='unary_unary: %s' % request.text)

    def DoUnaryStream(self, request, context):
        if request.timesout:
            while context.is_active():
                time.sleep(0.1)
        for i in range(request.count):
            yield Message(text='unary_stream: %s' % request.text)

    def DoStreamUnary(self, request_iter, context):
        for request in request_iter:
            if request.timesout:
                while context.is_active():
                    time.sleep(0.1)
            return Message(text='stream_unary: %s' % request.text)

    def DoStreamStream(self, request_iter, context):
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


class CatApplicationServicer(_SampleApplicationServicer):

    def extract_cat_value(self, metadata):
        for k, v in metadata:
            if k != 'x-newrelic-trace':
                continue
            return Message(text='%s' % v)

        return Message(text='')

    def DoUnaryUnary(self, request, context):
        return self.extract_cat_value(context.invocation_metadata())

    def DoUnaryStream(self, request, context):
        yield self.extract_cat_value(context.invocation_metadata())

    def DoStreamUnary(self, request_iter, context):
        list(request_iter)  # consume iterator
        return self.extract_cat_value(context.invocation_metadata())

    def DoStreamStream(self, request_iter, context):
        for request in request_iter:
            yield self.extract_cat_value(context.invocation_metadata())
