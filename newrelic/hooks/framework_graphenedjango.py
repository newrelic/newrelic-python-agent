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

import sys
import json
from inspect import isawaitable

from newrelic.common.signature import bind_args
from newrelic.api.error_trace import ErrorTrace
from newrelic.api.graphql_trace import GraphQLOperationTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.core.graphql_utils import graphql_statement
from newrelic.hooks.framework_graphql_py3 import (
    nr_coro_graphql_impl_wrapper,
)
from newrelic.hooks.framework_graphql import (
    ignore_graphql_duplicate_exception,
    GRAPHQL_VERSION
)

GRAPHENE_DJANGO_VERSION = get_package_version("graphene_django")
graphene_django_version_tuple = tuple(map(int, GRAPHENE_DJANGO_VERSION.split(".")))


def wrap_GraphQLView_get_response(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    string_response, status_code = wrapped(*args, **kwargs)
    response = json.loads(string_response)
    transaction.process_response(status_code, response)
    
    return string_response, status_code


def wrap_GraphQLView_execute_graphql_request(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_framework_info(name="GraphQL", version=GRAPHQL_VERSION)
    transaction.add_framework_info(name="GrapheneDjango", version=GRAPHENE_DJANGO_VERSION)
    bound_args = bind_args(wrapped, args, kwargs)

    try:
        schema = instance.schema.graphql_schema
        query = bound_args.get("query", None)
    except TypeError:
        return wrapped(*args, **kwargs)

    transaction.set_transaction_name(callable_name(wrapped), "GraphQL", priority=12)

    trace = GraphQLOperationTrace()

    trace.statement = graphql_statement(query)
    trace.product = "GrapheneDjango"

    # Handle Schemas created from frameworks
    if hasattr(schema, "_nr_framework"):
        framework = schema._nr_framework
        # trace.product = framework[0]
        transaction.add_framework_info(name=framework[0], version=framework[1])

    # Trace must be manually started and stopped to ensure it exists prior to and during the entire duration of the query.
    # Otherwise subsequent instrumentation will not be able to find an operation trace and will have issues.
    trace.__enter__()
    try:
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            result = wrapped(*args, **kwargs)
    except Exception:
        # Execution finished synchronously, exit immediately.
        trace.__exit__(*sys.exc_info())
        raise
    else:
        trace.set_transaction_name(priority=14)
        if isawaitable(result):
            # Asynchronous implementations
            # Return a coroutine that handles closing the operation trace
            return nr_coro_graphql_impl_wrapper(wrapped, trace, ignore_graphql_duplicate_exception, result)
        else:
            # Execution finished synchronously, exit immediately.
            trace.__exit__(None, None, None)
            return result


def instrument_graphene_django_views(module):
    if hasattr(module, "GraphQLView") and hasattr(module.GraphQLView, "execute_graphql_request"):
        wrap_function_wrapper(module, "GraphQLView.execute_graphql_request", wrap_GraphQLView_execute_graphql_request)

    if hasattr(module, "GraphQLView") and hasattr(module.GraphQLView, "get_response"):
        wrap_function_wrapper(module, "GraphQLView.get_response", wrap_GraphQLView_get_response)
        