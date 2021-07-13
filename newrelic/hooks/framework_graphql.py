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

from newrelic.api.error_trace import ErrorTrace, ErrorTraceWrapper
from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper
from newrelic.api.graphql_trace import GraphQLResolverTrace, GraphQLOperationTrace
from newrelic.api.time_trace import notice_error, current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name, parse_exc_info
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.core.graphql_utils import graphql_statement
from collections import deque
from copy import copy


def graphql_version():
    from graphql import __version__ as version
    return tuple(int(v) for v in version.split("."))


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


# def wrap_execute(wrapped, instance, args, kwargs):
#     transaction = current_transaction()
#     if transaction is None:
#         return wrapped(*args, **kwargs)
    
#     transaction.set_transaction_name(callable_name(wrapped), priority=1)
#     with GraphQLOperationTrace():
#         with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
#             return wrapped(*args, **kwargs)


def bind_operation_v3(operation, root_value):
    return operation

def bind_operation_v2(exe_context, operation, root_value):
    return operation


def wrap_execute_operation(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    trace = current_trace()

    if transaction:
        try:
            operation = bind_operation_v3(*args, **kwargs)
        except TypeError:
            operation = bind_operation_v2(*args, **kwargs)

        operation_name = operation.name
        if hasattr(operation_name, "value"):
            operation_name = operation_name.value
        trace.operation_name = operation_name = operation_name or "<anonymous>"

        operation_type = operation.operation
        if hasattr(operation_type, "name"):
            operation_type = operation_type.name.lower()
        trace.operation_type = operation_type = operation_type or "<unknown>"

        if operation.selection_set is not None:
            fields = operation.selection_set.selections
            try:
                deepest_path = traverse_deepest_path(fields)
            except:
                deepest_path = []
            trace.deepest_path = deepest_path = ".".join(deepest_path) or "<unknown>"

        transaction_name = "%s/%s/%s" % (operation_type, operation_name, deepest_path)
        transaction.set_transaction_name(transaction_name, "GraphQL", priority=11)

    return wrapped(*args, **kwargs)


def traverse_deepest_path(fields):
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
                inputs.append((inner_field, copy(current_path), current_path_len))

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

    if graphql_version() <= (3, 0, 0):
        bind_resolve_field = bind_resolve_field_v2
    else:
        bind_resolve_field = bind_resolve_field_v3

    parent_type, field_asts, field_path = bind_resolve_field(*args, **kwargs)

    field_name = field_asts[0].name.value

    with GraphQLResolverTrace(field_name) as trace:
        with ErrorTrace():
            trace._add_agent_attribute("graphql.field.parentType", parent_type.name)
            if isinstance(field_path, list):
                trace._add_agent_attribute("graphql.field.path", field_path[0])
            else:
                trace._add_agent_attribute("graphql.field.path", field_path.key)

            return wrapped(*args, **kwargs)


def bind_graphql_impl_query(schema, source, *args, **kwargs):
    return source


def bind_execute_graphql_query(
    schema,
    request_string="",
    root=None,
    context=None,
    variables=None,
    operation_name=None,
    middleware=None,
    backend=None,
    **execute_options):

    return request_string


def wrap_graphql_impl(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    version = graphql_version()
    framework_version = '.'.join(map(str, version))

    transaction.add_framework_info(name='GraphQL', version=framework_version)

    if graphql_version() <= (3, 0, 0):
        bind_query = bind_execute_graphql_query
    else:
        bind_query = bind_graphql_impl_query

    query = bind_query(*args, **kwargs)
    if hasattr(query, "body"):
        query = query.body

    with GraphQLOperationTrace() as trace:
        trace.statement = graphql_statement(query)
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            return wrapped(*args, **kwargs)


def instrument_graphql_execute(module):
    # if hasattr(module, "execute"):
    #     wrap_function_wrapper(module, "execute", wrap_execute)
    if hasattr(module, "ExecutionContext"):
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
    pass


def instrument_graphql_execution_middleware(module):
    if hasattr(module, "get_middleware_resolvers"):
        wrap_function_wrapper(
            module, "get_middleware_resolvers", wrap_get_middleware_resolvers
        )


def instrument_graphql_error_located_error(module):
    if hasattr(module, "located_error"):
        wrap_function_wrapper(module, "located_error", wrap_error_handler)


def instrument_graphql_validate(module):
    wrap_function_wrapper(module, "validate", wrap_validate)

def instrument_graphql(module):
    if hasattr(module, "graphql_impl"):
        wrap_function_wrapper(module, "graphql_impl", wrap_graphql_impl)
    if hasattr(module, "execute_graphql"):
        wrap_function_wrapper(module, "execute_graphql", wrap_graphql_impl)
