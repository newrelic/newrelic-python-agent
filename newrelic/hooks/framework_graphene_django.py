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

# import sys

from newrelic.api.error_trace import ErrorTrace
from newrelic.api.graphql_trace import GraphQLOperationTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper

# from newrelic.core.graphql_utils import graphql_statement
from newrelic.hooks.framework_graphene import (
    framework_details as graphene_framework_details,
)
from newrelic.hooks.framework_graphql import (
    framework_version as graphql_framework_version,
)
from newrelic.hooks.framework_graphql import ignore_graphql_duplicate_exception


def graphene_django_version():
    import graphene_django

    try:
        return tuple(int(x) for x in graphene_django.__version__.split("."))
    except Exception:
        return (0, 0, 0)


def bind_execute(query, *args, **kwargs):
    return query


def wrap_execute_graphql_request(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if not transaction:
        return wrapped(*args, **kwargs)

    # Return early for versions where this wrapper is unnecessary
    version = graphene_django_version()
    if version >= (3,) or not version:
        return wrapped(*args, **kwargs)

    try:
        query = bind_execute(*args, **kwargs)
    except TypeError:
        return wrapped(*args, **kwargs)

    framework = graphene_framework_details()
    transaction.add_framework_info(name=framework[0], version=framework[1])
    transaction.add_framework_info(name="GraphQL", version=graphql_framework_version())

    if hasattr(query, "body"):
        query = query.body

    transaction.set_transaction_name(callable_name(wrapped), "GraphQL", priority=10)

    with GraphQLOperationTrace(source=wrapped) as trace:
        trace.product = "Graphene"
        # breakpoint()
        # trace.statement = graphql_statement(query)
        with ErrorTrace(ignore=ignore_graphql_duplicate_exception):
            return wrapped(*args, **kwargs)


def instrument_graphene_django_views(module):
    if hasattr(module, "GraphQLView"):
        wrap_function_wrapper(module, "GraphQLView.execute_graphql_request", wrap_execute_graphql_request)
