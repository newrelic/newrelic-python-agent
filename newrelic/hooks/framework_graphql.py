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

from newrelic.api.time_trace import notice_error, current_trace
from newrelic.api.error_trace import ErrorTrace, ErrorTraceWrapper
from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper
from newrelic.api.graphql_trace import GraphQLResolverTrace, GraphQLTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name, parse_exc_info
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from collections import deque


def ignore_graphql_duplicate_exception(exc, val, tb):
    from graphql.error import GraphQLError

    if isinstance(val, GraphQLError):
        transaction = current_transaction()

        # Check that we have not recorded this exception
        # previously for this transaction due to multiple
        # error traces triggering. This happens if an exception
        # is reraised by GraphQL as a new GraphQLError type
        # after the original exception has already been recorded.

        if transaction and hasattr(val, "original_error"):
            _, _, fullnames, message = parse_exc_info((None, val.original_error, None))
            fullname = fullnames[0]
            for error in transaction._errors:
                if error.type == fullname and error.message == message:
                    return True

    return None  # Follow original exception matching rules


def wrap_execute(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)
    
    transaction.set_transaction_name(callable_name(wrapped), priority=1)
    with GraphQLTrace():
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            return wrapped(*args, **kwargs)


def wrap_executor_context_init(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    # Executors are arbitrary and swappable, but expose the same execute api
    executor = getattr(instance, "executor", None)
    if executor is not None:
        if hasattr(executor, "execute"):
            executor.execute = wrap_executor_execute(executor.execute)

    if hasattr(instance, "field_resolver"):
        if not hasattr(instance.field_resolver, "_nr_wrapped"):
            instance.field_resolver = wrap_resolver(instance.field_resolver)
            instance.field_resolver._nr_wrapped = True

    return result


def bind_operation_v3(operation, root_value):
    return operation

def bind_operation_v2(exe_context, operation, root_value):
    return operation


def wrap_execute_operation(wrapped, instance, args, kwargs):
    trace = current_trace()

    if trace:
        try:
            operation = bind_operation_v3(*args, **kwargs)
        except TypeError:
            operation = bind_operation_v2(*args, **kwargs)

        operation_name = operation.name
        if hasattr(operation_name, "value"):
            operation_name = operation_name.value
        if operation_name:
            trace._add_agent_attribute("graphql.operation.name", operation_name)

        operation_type = operation.operation
        if hasattr(operation_type, "name"):
            operation_type = operation_type.name
        if operation_type:
            trace._add_agent_attribute("graphql.operation.type", operation_type.lower())

        if operation.selection_set is not None:
            fields = operation.selection_set.selections
            deepest_path = traverse_deepest_path(fields)

            if deepest_path is None:
                deepest_path_str = "<unknown>"
            else:
                deepest_path_str = ".".join(deepest_path)
            trace._add_agent_attribute("graphql.operation.deepestPath", deepest_path_str)

    return wrapped(*args, **kwargs)


def traverse_deepest_path(fields):
    from graphql import GraphQLScalarType

    inputs = deque(((field, deque(), 0) for field in fields))
    deepest_path_len = 0
    deepest_path = None

    while inputs:
        field, current_path, current_path_len = inputs.pop()

        field_name = field.name
        if hasattr(field_name, "value"):
            field_name = field_name.value

        current_path.append(field_name)
        current_path_len += 1

        if field.selection_set is None or len(field.selection_set.selections) == 0:
            if deepest_path_len < current_path_len:
                deepest_path = current_path
                deepest_path_len = current_path_len
        else:
            for inner_field in field.selection_set.selections:
                if not isinstance(inner_field, GraphQLScalarType):
                    inputs.append((inner_field, current_path, current_path_len))

    return deepest_path


def bind_get_middleware_resolvers(middlewares):
    return middlewares


def wrap_get_middleware_resolvers(wrapped, instance, args, kwargs):
    middlewares = bind_get_middleware_resolvers(*args, **kwargs)
    middlewares = [FunctionTraceWrapper(ErrorTraceWrapper(m, ignore=ignore_graphql_duplicate_exception)) if not hasattr(m, "_nr_wrapped") else m for m in middlewares]
    for m in middlewares:
        m._nr_wrapped = True

    return wrapped(middlewares)


def bind_get_field_resolver(field_resolver):
    return field_resolver


def wrap_get_field_resolver(wrapped, instance, args, kwargs):
    resolver = bind_get_field_resolver(*args, **kwargs)
    if not hasattr(resolver, "_nr_wrapped"):
        resolver = wrap_resolver(resolver)
        resolver._nr_wrapped = True

    return wrapped(resolver)


def wrap_get_field_def(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    if hasattr(result, "resolve"):
        if not hasattr(result.resolve, "_nr_wrapped"):
            result.resolve = wrap_resolver(result.resolve)
            result.resolve._nr_wrapped = True

    return result


@function_wrapper
def wrap_executor_execute(wrapped, instance, args, kwargs):
    # args[0] is the resolver function, or the top of the middleware chain
    args = list(args)
    if callable(args[0]):
        if not hasattr(args[0], "_nr_wrapped"):
            args[0] = wrap_resolver(args[0])
            args[0]._nr_wrapped = True
    return wrapped(*args, **kwargs)


@function_wrapper
def wrap_resolver(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    # Prevent double wrapping using _nr_wrapped attr
    if transaction is None:
        return wrapped(*args, **kwargs)

    transaction.set_transaction_name(callable_name(wrapped), priority=2)
    with FunctionTrace(callable_name(wrapped)):
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            return wrapped(*args, **kwargs)


def wrap_error_handler(wrapped, instance, args, kwargs):
    notice_error(ignore=ignore_graphql_duplicate_exception)
    return wrapped(*args, **kwargs)


def wrap_validate(wrapped, instance, args, kwargs):
    errors = wrapped(*args, **kwargs)

    # Raise errors and immediately catch them so we can record them
    for error in errors:
        try:
            raise error
        except:
            notice_error(ignore=ignore_graphql_duplicate_exception)

    return errors


def bind_resolve_field_v3(parent_type, source, field_nodes, path):
    return parent_type, field_nodes, path


def bind_resolve_field_v2(exe_context, parent_type, source, field_asts, parent_info, field_path):
    return parent_type, field_asts, field_path


def wrap_resolve_field(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if transaction is None:
        return wrapped(*args, **kwargs)

    from graphql import __version__ as version
    version = tuple(int(v) for v in version.split("."))

    if version <= (3, 0, 0):
        bind_resolve_field = bind_resolve_field_v2
    else:
        bind_resolve_field = bind_resolve_field_v3

    parent_type, field_asts, field_path = bind_resolve_field(*args, **kwargs)

    field_name = field_asts[0].name.value

    with GraphQLResolverTrace(field_name) as trace:
        trace._add_agent_attribute("graphql.field.name", field_name)
        trace._add_agent_attribute("graphql.field.parentType", parent_type.name)
        if isinstance(field_path, list):
            trace._add_agent_attribute("graphql.field.path", field_path[0])
        else:
            trace._add_agent_attribute("graphql.field.path", field_path.key)

        return wrapped(*args, **kwargs)


def instrument_graphql_execute(module):
    if hasattr(module, "execute"):
        wrap_function_wrapper(module, "execute", wrap_execute)
    if hasattr(module, "get_field_def"):
        wrap_function_wrapper(module, "get_field_def", wrap_get_field_def)
    if hasattr(module, "ExecutionContext"):
        wrap_function_wrapper(
            module, "ExecutionContext.__init__", wrap_executor_context_init
        )
        if hasattr(module.ExecutionContext, "resolve_field"):
            wrap_function_wrapper(
                module, "ExecutionContext.resolve_field", wrap_resolve_field
            )
        if hasattr(module.ExecutionContext, "execute_operation"):
            wrap_function_wrapper(
                module, "ExecutionContext.execute_operation", wrap_execute_operation
            )

    if hasattr(module, "resolve_field"):
        wrap_function_wrapper(module, "resolve_field", wrap_resolve_field)

    if hasattr(module, "execute_operation"):
        wrap_function_wrapper(
            module, "execute_operation", wrap_execute_operation
        )

def instrument_graphql_execution_utils(module):
    if hasattr(module, "ExecutionContext"):
        wrap_function_wrapper(
            module, "ExecutionContext.__init__", wrap_executor_context_init
        )


def instrument_graphql_execution_middleware(module):
    if hasattr(module, "get_middleware_resolvers"):
        wrap_function_wrapper(
            module, "get_middleware_resolvers", wrap_get_middleware_resolvers
        )
    if hasattr(module, "MiddlewareManager"):
        wrap_function_wrapper(
            module, "MiddlewareManager.get_field_resolver", wrap_get_field_resolver
        )


def instrument_graphql_error_located_error(module):
    if hasattr(module, "located_error"):
        wrap_function_wrapper(module, "located_error", wrap_error_handler)


def instrument_graphql_validate(module):
    wrap_function_wrapper(module, "validate", wrap_validate)
