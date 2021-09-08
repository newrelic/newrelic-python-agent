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
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.graphql_trace import GraphQLOperationTrace, GraphQLResolverTrace
from newrelic.api.time_trace import current_trace, notice_error
from newrelic.api.transaction import current_transaction, ignore_transaction
from newrelic.common.object_names import callable_name, parse_exc_info
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.core.graphql_utils import graphql_statement
from newrelic.hooks.framework_graphql import ignore_graphql_duplicate_exception

def bind_graphql(schema, data, *args, **kwargs):
    return schema, data

def wrap_graphql(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    try:
        schema, data = bind_graphql(*args, **kwargs)
    except TypeError:
        return wrapped(*args, **kwargs)

    query = data["query"]
    if hasattr(query, "body"):
        query = query.body

    operation_type = schema.query_type.name.lower() or schema.mutation_type.name.lower() or schema.subscription_type.name.lower()
    transaction.set_transaction_name(callable_name(wrapped), "GraphQL", priority=10)

    with GraphQLOperationTrace() as trace:
        trace.statement = graphql_statement(query)
        trace.operation_name = data["operationName"] or "<anonymous>"
        trace.operation_type = operation_type or "<unknown>"
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            result = wrapped(*args, **kwargs)
            return result


def instrument_ariadne_execute(module):
    if hasattr(module, "graphql"):
        wrap_function_wrapper(module, "graphql", wrap_graphql)
