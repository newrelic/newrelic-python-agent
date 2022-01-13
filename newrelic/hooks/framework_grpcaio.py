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

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.web_transaction import WebTransactionWrapper, WebTransaction
from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import notice_error
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.common.object_names import callable_name


# def grpc_web_transaction(wrapped, instance, args, kwargs):
#     rpc_event, behavior = _bind_transaction_args(*args, **kwargs)
#     behavior_name = callable_name(behavior)

#     call_details = (
#             getattr(rpc_event, 'call_details', None) or
#             getattr(rpc_event, 'request_call_details', None))

#     metadata = (
#             getattr(rpc_event, 'invocation_metadata', None) or
#             getattr(rpc_event, 'request_metadata', None))

#     host = port = None
#     if call_details:
#         try:
#             host, port = call_details.host.split(b':', 1)
#         except Exception:
#             pass

#         request_path = call_details.method

#     return WebTransactionWrapper(
#             wrapped,
#             name=behavior_name,
#             request_path=request_path,
#             host=host,
#             port=port,
#             headers=metadata)(*args, **kwargs)

HANDLER_METHODS = ("unary_unary", "stream_unary", "unary_stream", "stream_stream")

@function_wrapper
def _prepare_request(wrapped, instance, args, kwargs):
    breakpoint()

    return WebTransactionWrapper(wrapped)(*args, **kwargs)

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
                    handler[method] = _prepare_request(handler_method)

            return RpcMethodHandler(**handler)

    return _NR_Interceptor()


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


def instrument_grpc_server(module):
    if hasattr(module, "Server"):
        wrap_function_wrapper(module.Server, "__init__", wrap_server_init)
