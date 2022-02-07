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

import asyncio
import grpc
import pytest
import six

from newrelic.api.background_task import background_task
from newrelic.core.config import global_settings

from testing_support.fixtures import (validate_transaction_metrics,
        validate_transaction_errors, override_generic_settings)

from framework_grpc._test_common import create_request
from _test_common import get_result


_test_matrix = [
    ('service_method_type,raises_exception,message_count,cancel'), (
        ('unary_unary', False, 1, False),
        ('unary_unary', True, 1, False),

        ('stream_unary', False, 1, False),
        ('stream_unary', True, 1, False),

        ('unary_stream', False, 1, False),
        ('unary_stream', True, 1, False),
        ('unary_stream', False, 2, False),
        ('unary_stream', True, 2, False),
        ('unary_stream', False, 1, True),
        ('unary_stream', False, 2, True),

        ('stream_stream', False, 1, False),
        ('stream_stream', True, 1, False),
        ('stream_stream', False, 2, False),
        ('stream_stream', True, 2, False),
        ('stream_stream', False, 1, True),
        ('stream_stream', False, 2, True),

        # ('unary_unary', False, 1, False),
        # ('unary_unary', True, 1, False),

        # ('stream_unary', False, 1, False),
        # ('stream_unary', True, 1, False),

        # ('unary_stream', False, 1, False),
        # ('unary_stream', False, 2, False),

        # ('stream_stream', False, 1, False),
        # ('stream_stream', False, 2, False),
)]

@pytest.mark.parametrize(*_test_matrix)
def test_client_newrelic_disabled_no_harm(service_method_type, raises_exception, message_count, cancel, mock_grpc_server, stub):
    import asyncio

    port = mock_grpc_server

    service_method_class_name = 'NoTxn%s%s' % (
            service_method_type.title().replace('_', ''),
            'Raises' if raises_exception else '')
    streaming_request = service_method_type.split('_')[0] == 'stream'
    streaming_response = service_method_type.split('_')[1] == 'stream'

    _errors = []
    if not streaming_response and cancel:
        _errors.append('grpc:FutureCancelledError')
    elif raises_exception or cancel:
        _errors.append('grpc._channel:_Rendezvous')

    @override_generic_settings(global_settings(), {'enabled': False})
    def _test_client():
        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = service_method_class.__call__

        # In the case that we're preparing to cancel a request it's important
        # that the request does not return prior to cancelling. If the request
        # returns prior to cancellation then the response might be valid. In
        # order to force the request to not return, the timesout option is set.

        request = create_request(streaming_request, count=message_count,
                timesout=cancel)

        reply = service_method_method(request, timeout=3)

        if cancel:
            reply.cancel()

        try:
            # If the reply was canceled or the server code raises an exception,
            # this will raise an exception which will be recorded by the agent
            reply = get_result(reply)
        except (AttributeError, TypeError):
            reply = [reply]

        expected_text = '%s: Hello World' % service_method_type
        response_texts_correct = [r.text == expected_text for r in reply]
        assert len(response_texts_correct) == message_count
        assert response_texts_correct and all(response_texts_correct), reply

    try:
        _test_client()
    except grpc.RpcError as e:
        if raises_exception:
            assert '%s: Hello World' % service_method_type in e.details()
        elif cancel:
            assert e.code() == grpc.StatusCode.CANCELLED
        else:
            raise
    except (grpc.FutureCancelledError, asyncio.CancelledError):
        assert cancel


class ClientInterceptor(grpc.aio.ClientInterceptor):
    async def intercept_unary_unary(self, continuation, client_call_details, request):
        breakpoint()
        return


@pytest.mark.parametrize(*_test_matrix)
def test_client(service_method_type, raises_exception, message_count, cancel, mock_grpc_server, stub_and_channel):
    stub, channel = stub_and_channel

    port = mock_grpc_server

    service_method_class_name = 'NoTxn%s%s' % (
            service_method_type.title().replace('_', ''),
            'Raises' if raises_exception else '')
    streaming_request = service_method_type.split('_')[0] == 'stream'
    streaming_response = service_method_type.split('_')[1] == 'stream'

    _test_scoped_metrics = [
            # ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
            #     service_method_class_name), 1),
    ]
    _test_rollup_metrics = [
            # ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
            #     service_method_class_name), 1),
            # ('External/localhost:%s/all' % port, 1),
            ('External/allOther', 1),
            ('External/all', 1),
    ]

    if six.PY2:
        _test_transaction_name = 'test_clients:_test_client'
    else:
        _test_transaction_name = (
                'test_clients:test_client.<locals>._test_client')

    _errors = []
    if not streaming_response and cancel:
        _errors.append('grpc:FutureCancelledError')
    elif raises_exception or cancel:
        _errors.append('grpc._channel:_Rendezvous')

    @validate_transaction_errors(errors=_errors)
    @validate_transaction_metrics(_test_transaction_name,
            scoped_metrics=_test_scoped_metrics,
            rollup_metrics=_test_rollup_metrics,
            background_task=True)
    @background_task()
    def _test_client():
        service_method_class = getattr(stub, service_method_class_name)
        service_method_method = service_method_class.__call__

        # service_method_class._interceptors = [ClientInterceptor()]

        # In the case that we're preparing to cancel a request it's important
        # that the request does not return prior to cancelling. If the request
        # returns prior to cancellation then the response might be valid. In
        # order to force the request to not return, the timesout option is set.

        request = create_request(streaming_request, count=message_count,
                timesout=cancel)

        reply = service_method_method(request, timeout=3)

        if cancel:
            reply.cancel()

        try:
            # If the reply was canceled or the server code raises an exception,
            # this will raise an exception which will be recorded by the agent
            reply = get_result(reply)
        except (AttributeError, TypeError):
            reply = [reply]

        expected_text = '%s: Hello World' % service_method_type
        response_texts_correct = [r.text == expected_text for r in reply]
        assert len(response_texts_correct) == message_count
        assert response_texts_correct and all(response_texts_correct), reply


    try:
        _test_client()
    except grpc.RpcError as e:
        if raises_exception:
            assert '%s: Hello World' % service_method_type in e.details()
        elif cancel:
            assert e.code() == grpc.StatusCode.CANCELLED
        else:
            raise
    except (grpc.FutureCancelledError, asyncio.exceptions.CancelledError):
        assert cancel


# _test_matrix = [
#     ('service_method_type,service_method_method_name,future_response'), (
#         ('unary_unary', '__call__', False),
#         ('unary_unary', 'with_call', False),
#         ('unary_unary', 'future', True),

#         ('stream_unary', '__call__', False),
#         ('stream_unary', 'with_call', False),
#         ('stream_unary', 'future', True),

#         ('unary_stream', '__call__', True),

#         ('stream_stream', '__call__', True),
# )]


# @pytest.mark.parametrize(*_test_matrix)
# def test_future_timeout_error(service_method_type, service_method_method_name,
#         future_response, mock_grpc_server, stub):
#     port = mock_grpc_server

#     service_method_class_name = 'NoTxn%s' % (
#             service_method_type.title().replace('_', ''))
#     streaming_request = service_method_type.split('_')[0] == 'stream'

#     _test_scoped_metrics = [
#             ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
#                 service_method_class_name), 1),
#     ]
#     _test_rollup_metrics = [
#             ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
#                 service_method_class_name), 1),
#             ('External/localhost:%s/all' % port, 1),
#             ('External/allOther', 1),
#             ('External/all', 1),
#     ]

#     if six.PY2:
#         _test_transaction_name = 'test_clients:_test_future_timeout_error'
#     else:
#         _test_transaction_name = (
#                 'test_clients:test_future_timeout_error.<locals>.'
#                 '_test_future_timeout_error')

#     @validate_transaction_errors(errors=[])
#     @validate_transaction_metrics(_test_transaction_name,
#             scoped_metrics=_test_scoped_metrics,
#             rollup_metrics=_test_rollup_metrics,
#             background_task=True)
#     @background_task()
#     def _test_future_timeout_error():
#         service_method_class = getattr(stub, service_method_class_name)
#         service_method_method = getattr(service_method_class,
#                 service_method_method_name)

#         request = create_request(streaming_request, count=1, timesout=True)

#         reply = get_result(service_method_method, request, timeout=0.01)
#         assert reply and reply.code() == grpc.StatusCode.DEADLINE_EXCEEDED

#     _test_future_timeout_error()


# _test_matrix = [
#     ('service_method_type,service_method_method_name'), (
#         ('unary_unary', 'with_call'),
#         ('unary_unary', 'future'),

#         ('stream_unary', 'with_call'),
#         ('stream_unary', 'future'),

# )]


# @pytest.mark.parametrize(*_test_matrix)
# def test_repeated_result(service_method_type, service_method_method_name,
#         mock_grpc_server, stub):
#     port = mock_grpc_server

#     service_method_class_name = 'NoTxn%s' % (
#             service_method_type.title().replace('_', ''))
#     streaming_request = service_method_type.split('_')[0] == 'stream'

#     _test_scoped_metrics = [
#             ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
#                 service_method_class_name), 1),
#     ]
#     _test_rollup_metrics = [
#             ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
#                 service_method_class_name), 1),
#             ('External/localhost:%s/all' % port, 1),
#             ('External/allOther', 1),
#             ('External/all', 1),
#     ]

#     if six.PY2:
#         _test_transaction_name = 'test_clients:_test_repeated_result'
#     else:
#         _test_transaction_name = (
#                 'test_clients:'
#                 'test_repeated_result.<locals>._test_repeated_result')

#     @validate_transaction_errors(errors=[])
#     @validate_transaction_metrics(_test_transaction_name,
#             scoped_metrics=_test_scoped_metrics,
#             rollup_metrics=_test_rollup_metrics,
#             background_task=True)
#     @background_task()
#     def _test_repeated_result():
#         service_method_class = getattr(stub, service_method_class_name)
#         service_method_method = getattr(service_method_class,
#                 service_method_method_name)

#         request = create_request(streaming_request, count=1, timesout=False)

#         reply = service_method_method(request)
#         if isinstance(reply, tuple):
#             reply = reply[1]

#         reply.result()
#         reply.result()

#     _test_repeated_result()


# _test_matrix = [
#     ('service_method_type,service_method_method_name,future_response'), (
#         ('unary_stream', '__call__', True),
#         ('stream_stream', '__call__', True),
# )]


# @pytest.mark.parametrize(*_test_matrix)
# def test_future_cancel(service_method_type, service_method_method_name,
#         future_response, mock_grpc_server, stub):
#     port = mock_grpc_server

#     service_method_class_name = 'NoTxn%s' % (
#             service_method_type.title().replace('_', ''))
#     streaming_request = service_method_type.split('_')[0] == 'stream'

#     _test_scoped_metrics = [
#             ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
#                 service_method_class_name), 1),
#     ]
#     _test_rollup_metrics = [
#             ('External/localhost:%s/gRPC/SampleApplication/%s' % (port,
#                 service_method_class_name), 1),
#             ('External/localhost:%s/all' % port, 1),
#             ('External/allOther', 1),
#             ('External/all', 1),
#     ]

#     if six.PY2:
#         _test_transaction_name = 'test_clients:_test_future_cancel'
#     else:
#         _test_transaction_name = (
#                 'test_clients:test_future_cancel.<locals>.'
#                 '_test_future_cancel')

#     @validate_transaction_errors(errors=[])
#     @validate_transaction_metrics(_test_transaction_name,
#             scoped_metrics=_test_scoped_metrics,
#             rollup_metrics=_test_rollup_metrics,
#             background_task=True)
#     @background_task()
#     def _test_future_cancel():
#         service_method_class = getattr(stub, service_method_class_name)
#         service_method_method = getattr(service_method_class,
#                 service_method_method_name)

#         request = create_request(streaming_request, count=3, timesout=False)

#         reply = service_method_method(request)
#         for result in reply:
#             reply.cancel()
#             break

#     _test_future_cancel()
