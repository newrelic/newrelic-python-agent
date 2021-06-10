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

from newrelic.api.error_trace import ErrorTrace
from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper, function_wrapper


def wrap_execute(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    transaction.set_transaction_name(callable_name(wrapped), priority=1)
    with FunctionTrace(callable_name(wrapped)):
        with ErrorTrace():
            return wrapped(*args, **kwargs)

def wrap_executor_context_init(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    # Executors are arbitrary and swappable, but expose the same execute api
    executor = getattr(instance, "executor", None)
    if executor is not None:
        if hasattr(executor, "execute"):
            executor.execute = wrap_executor_execute(executor.execute)

    return result

def bind_get_middleware_resolvers(middlewares):
    return middlewares

def wrap_get_middleware_resolvers(wrapped, instance, args, kwargs):
    middlewares = bind_get_middleware_resolvers(*args, **kwargs)
    middlewares = [FunctionTraceWrapper(m) for m in middlewares]
    for m in middlewares:
        m._nr_wrapped = True

    return wrapped(middlewares)

def bind_get_field_resolver(field_resolver):
    return field_resolver

def wrap_get_field_resolver(wrapped, instance, args, kwargs):
    resolver = bind_get_field_resolver(*args, **kwargs)
    return wrapped(wrap_resolver(resolver))

@function_wrapper
def wrap_executor_execute(wrapped, instance, args, kwargs):
    # args[0] is the resolver function, or the top of the middleware chain
    args = list(args)
    if callable(args[0]):
        args[0] = wrap_resolver(args[0])
    return wrapped(*args, **kwargs)

@function_wrapper
def wrap_resolver(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    # Prevent double wrapping using _nr_wrapped attr
    if transaction is None or hasattr(wrapped, "_nr_wrapped"):
        return wrapped(*args, **kwargs)

    transaction.set_transaction_name(callable_name(wrapped), priority=2)
    with FunctionTrace(callable_name(wrapped)):
        with ErrorTrace():
            return wrapped(*args, **kwargs)

def instrument_graphql_execute(module):
    wrap_function_wrapper(module, 'execute', wrap_execute)

def instrument_graphql_execution_utils(module):
    if hasattr(module, "ExecutorContext"):
        wrap_function_wrapper(module, 'ExecutorContext.__init__', wrap_executor_context_init)
    if hasattr(module, "ExecutionContext"):
        wrap_function_wrapper(module, 'ExecutionContext.__init__', wrap_executor_context_init)

def instrument_graphql_execution_middleware(module):
    if hasattr(module, "get_middleware_resolvers"):
        wrap_function_wrapper(module, 'get_middleware_resolvers', wrap_get_middleware_resolvers)
    if hasattr(module, "MiddlewareManager"):
        wrap_function_wrapper(module, 'MiddlewareManager.get_field_resolver', wrap_get_field_resolver)
