import time
from newrelic.api.transaction import current_transaction

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

    def NoTxnUnaryUnaryRaises(self, request, context):
        current_transaction().ignore_transaction = True
        raise AssertionError('unary_unary: %s' % request.text)

    def NoTxnUnaryStreamRaises(self, request, context):
        current_transaction().ignore_transaction = True
        raise AssertionError('unary_stream: %s' % request.text)

    def NoTxnStreamUnaryRaises(self, request_iter, context):
        current_transaction().ignore_transaction = True
        for request in request_iter:
            raise AssertionError('stream_unary: %s' % request.text)

    def NoTxnStreamStreamRaises(self, request_iter, context):
        current_transaction().ignore_transaction = True
        for request in request_iter:
            raise AssertionError('stream_stream: %s' % request.text)

    def NoTxnUnaryUnary(self, request, context):
        current_transaction().ignore_transaction = True
        return self.DoUnaryUnary(request, context)

    def NoTxnUnaryStream(self, request, context):
        current_transaction().ignore_transaction = True
        return self.DoUnaryStream(request, context)

    def NoTxnStreamUnary(self, request_iter, context):
        current_transaction().ignore_transaction = True
        return self.DoStreamUnary(request_iter, context)

    def NoTxnStreamStream(self, request_iter, context):
        current_transaction().ignore_transaction = True
        return self.DoStreamStream(request_iter, context)

    def extract_dt_value(self, metadata):
        for k, v in metadata:
            if k != 'newrelic':
                continue
            return Message(text='%s' % v)

        return Message(text='')

    def DtNoTxnUnaryUnary(self, request, context):
        current_transaction().ignore_transaction = True
        return self.extract_dt_value(context.invocation_metadata())

    def DtNoTxnUnaryStream(self, request, context):
        current_transaction().ignore_transaction = True
        yield self.extract_dt_value(context.invocation_metadata())

    def DtNoTxnStreamUnary(self, request_iter, context):
        current_transaction().ignore_transaction = True
        list(request_iter)  # consume iterator
        return self.extract_dt_value(context.invocation_metadata())

    def DtNoTxnStreamStream(self, request_iter, context):
        current_transaction().ignore_transaction = True
        for request in request_iter:
            yield self.extract_dt_value(context.invocation_metadata())
