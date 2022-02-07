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

from inspect import isawaitable
import random
import time
from newrelic.api.application import application_instance

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.web_transaction import WebTransactionWrapper, WebTransaction
from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import notice_error
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.common.object_names import callable_name


HANDLER_METHODS = ("unary_unary", "stream_unary", "unary_stream", "stream_stream")

def _nr_interceptor():
    from grpc.aio._interceptor import ServerInterceptor
    from grpc._utilities import RpcMethodHandler

    class _NR_Interceptor(ServerInterceptor):
        async def intercept_service(self, continuation, handler_call_details):
            handler = continuation(handler_call_details)
            if isawaitable(handler):
                handler = await handler

            handler = handler._asdict()
            for method in HANDLER_METHODS:
                handler_method = handler.get(method, None)
                if handler_method is not None:
                    handler[method] = grpc_web_transaction(handler_method, handler_call_details)

            return RpcMethodHandler(**handler)

    return _NR_Interceptor()


def _bind_context(request, context):
    return context


# def nr_server_callback(context, transaction):
#     def _nr_server_callback():
#         # Process status code and trailing metadata from ServicerContext
#         if transaction and transaction.state == transaction.STATE_RUNNING:
#             try:
#                 status_code = context.code()
#                 trailing_metadata = context.trailing_metadata()
#             except AttributeError:
#                 pass
#             else:
#                 transaction.process_response(status_code, trailing_metadata)

#     return _nr_server_callback

def grpc_web_transaction(handler_method, call_details):
    @function_wrapper
    def _grpc_web_transaction(wrapped, instance, args, kwargs):
        context = _bind_context(*args, **kwargs)
        behavior_name = callable_name(wrapped)

        metadata = (
                getattr(context, 'invocation_metadata', None) or
                getattr(context, 'request_metadata', None))()

        host = port = request_path = None
        try:
            host = context.host().decode("utf-8").split(":")[1:]  # Split host into pieces, removing protocol
            port = host[-1]  # Remove port
            host = ":".join(host[:-1])  # Rejoin ipv6 hosts
        except Exception:
            pass

        if call_details is not None:
            request_path = call_details.method

        with WebTransaction(
            application=application_instance(),
            name=behavior_name,
            request_path=request_path,
            host=host,
            port=port,
            headers=metadata) as transaction:

            response = wrapped(*args, **kwargs)

            try:
                status_code = context.code()
                trailing_metadata = context.trailing_metadata()
            except AttributeError:
                pass
            else:
                breakpoint()
                transaction.process_response(status_code, trailing_metadata)

            return response

    return _grpc_web_transaction(handler_method)


def bind_server_init_args(thread_pool, generic_handlers, interceptors, options, maximum_concurrent_rpcs, compression):
    return thread_pool, generic_handlers, interceptors, options, maximum_concurrent_rpcs, compression


def wrap_server_init(wrapped, instance, args, kwargs):
    args = list(bind_server_init_args(*args, **kwargs))
    interceptors = args[2]

    # Insert New Relic into interceptors
    if not interceptors:
        interceptors = [_nr_interceptor()]
    else:
        interceptors = list(interceptors)
        interceptors.insert(0, _nr_interceptor())

    args[2] = interceptors

    return wrapped(*args, **kwargs)


def _prepare_request(
        transaction,
        guid, 
        request,
        *args,
        timeout=None,
        metadata=None,
        **kwargs
    ):
    metadata = metadata and list(metadata) or []
    dt_metadata = transaction._create_distributed_trace_data_with_guid(guid)
    metadata.extend(
        transaction._generate_distributed_trace_headers(dt_metadata)
    )
    kwargs.update({"timeout": timeout, "metadata": metadata})
    args = (request,) + args
    return args, kwargs


def _prepare_request_stream(
        transaction, guid, request_iterator, *args, **kwargs):
    return _prepare_request(
            transaction, guid, request_iterator, *args, **kwargs)

def _get_uri_method(instance, *args, **kwargs):
    if hasattr(instance._channel, "target"):
        target = instance._channel.target().decode('utf-8')
    else:
        target = "<unknown>"

    method = instance._method.decode('utf-8').lstrip('/')
    uri = 'grpc://%s/%s' % (target, method)
    return (uri, method)


def await_response(trace):
    def _await_response(call):
        """Retrieve status code using an event loop."""
        transaction = current_transaction()
        if transaction:
            import asyncio
            loop = asyncio.get_event_loop()
            code, trailing_metadata = loop.run_until_complete(asyncio.gather(call.code(), call.trailing_metadata()))
            breakpoint()
            trace.process_response(code.value[0], trailing_metadata)

    return _await_response


def wrap_call(module, object_path, prepare):

    def _call_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if transaction is None:
            return wrapped(*args, **kwargs)

        uri, method = _get_uri_method(instance)
        with ExternalTrace('gRPC', uri, method) as trace:
            args, kwargs = prepare(transaction, None, *args, **kwargs)
            call = wrapped(*args, **kwargs)
            call.add_done_callback(await_response(trace))

        return call

    wrap_function_wrapper(module, object_path, _call_wrapper)


def instrument_grpc_aio_channel(module):
    wrap_call(module, 'UnaryUnaryMultiCallable.__call__',
            _prepare_request)
    wrap_call(module, 'StreamUnaryMultiCallable.__call__',
            _prepare_request_stream)
    wrap_call(module, 'UnaryStreamMultiCallable.__call__',
            _prepare_request)
    wrap_call(module, 'StreamStreamMultiCallable.__call__',
            _prepare_request_stream)
    # wrap_future(module, '_UnaryStreamMultiCallable.__call__',
    #         _prepare_request)
    # wrap_future(module, '_StreamStreamMultiCallable.__call__',
    #         _prepare_request_stream)

    # if hasattr(module, '_MultiThreadedRendezvous'):
    #     wrap_function_wrapper(module, '_MultiThreadedRendezvous.result',
    #             wrap_result)
    #     wrap_function_wrapper(module, '_MultiThreadedRendezvous._next',
    #             wrap_next)
    # else:
    #     wrap_function_wrapper(module, '_Rendezvous.result',
    #             wrap_result)
    #     wrap_function_wrapper(module, '_Rendezvous._next',
    #             wrap_next)
    # wrap_function_wrapper(module, '_Rendezvous.cancel',
    #         wrap_result)


def instrument_grpc_aio_server(module):
    if hasattr(module, "Server"):
        wrap_function_wrapper(module.Server, "__init__", wrap_server_init)
