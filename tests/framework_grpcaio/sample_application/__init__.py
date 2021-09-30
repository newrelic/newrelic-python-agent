# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import time
from newrelic.api.transaction import current_transaction
import grpc

from sample_application_pb2 import Message
from sample_application_pb2_grpc import (
        SampleApplicationServicer as _SampleApplicationServicer)


class Status(object):
    code = grpc.StatusCode.ABORTED
    details = 'abort_with_status'
    trailing_metadata = {}


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

    def DoUnaryUnaryAbort(self, request, context):
        context.abort(grpc.StatusCode.ABORTED, 'aborting')

    def DoUnaryStreamAbort(self, request, context):
        context.abort(grpc.StatusCode.ABORTED, 'aborting')

    def DoStreamUnaryAbort(self, request_iter, context):
        context.abort(grpc.StatusCode.ABORTED, 'aborting')

    def DoStreamStreamAbort(self, request_iter, context):
        context.abort(grpc.StatusCode.ABORTED, 'aborting')

    def DoUnaryUnaryAbortWithStatus(self, request, context):
        context.abort_with_status(Status)

    def DoUnaryStreamAbortWithStatus(self, request, context):
        context.abort_with_status(Status)

    def DoStreamUnaryAbortWithStatus(self, request_iter, context):
        context.abort_with_status(Status)

    def DoStreamStreamAbortWithStatus(self, request_iter, context):
        context.abort_with_status(Status)

    def extract_dt_value(self, metadata):
        d = {k: v for k, v in metadata}
        return Message(text=json.dumps(d))

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
