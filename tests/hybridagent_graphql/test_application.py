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

import pytest
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from hybridagent_graphql.test_application_async import error_middleware_async, example_middleware_async
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version
from testing_support.util import conditional_decorator

graphql_version = get_package_version("graphql-core")

def to_graphql_source(query):
    def delay_import():
        try:
            from graphql import Source
        except ImportError:
            # Fallback if Source is not implemented
            return query

        return Source(query)

    return delay_import


def example_middleware(next, root, info, **args):  # noqa: A002
    return_value = next(root, info, **args)
    return return_value


def error_middleware(next, root, info, **args):  # noqa: A002
    raise RuntimeError("Runtime Error!")


def test_no_harm_no_transaction(target_application):
    _, target_application, _, _ = target_application

    def _test():
        target_application("{ __schema { types { name } } }")

    _test()


example_middleware = [example_middleware]
error_middleware = [error_middleware]

example_middleware.append(example_middleware_async)
error_middleware.append(error_middleware_async)

_runtime_error_name = callable_name(RuntimeError)
_test_runtime_error = [(_runtime_error_name, "Runtime Error!")]


def test_basic(target_application):
    framework, target_application, is_wsgi_or_asgi, _ = target_application
    if not is_wsgi_or_asgi:
        transaction_name = "hybridagent_graphql.test_application:test_basic.<locals>._test"
    elif framework == "Strawberry":
        transaction_name = "strawberry.asgi:GraphQL.__call__"
    elif (framework == "Ariadne") and (is_wsgi_or_asgi == "wsgi"):
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif framework == "Ariadne":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        response = target_application("{ hello }")
        assert response["hello"] == "Hello!"

    _test()


def test_transaction_empty_settings(target_application):
    _, target_application, _, _ = target_application

    @validate_transaction_metrics(
        "hybridagent_graphql.test_application:test_transaction_empty_settings.<locals>._test",
        background_task=True,
    )
    @background_task()
    def _test():
        transaction = current_transaction()
        settings = transaction._settings
        transaction._settings = None

        response = target_application("{ hello }")
        assert response["hello"] == "Hello!"

        transaction._settings = settings

    _test()


@dt_enabled
def test_query_and_mutation(target_application):
    framework, target_application, is_wsgi_or_asgi, _ = target_application

    if not is_wsgi_or_asgi:
        mutation_transaction_name = "hybridagent_graphql.test_application:test_query_and_mutation.<locals>._mutation"
        query_transaction_name = "hybridagent_graphql.test_application:test_query_and_mutation.<locals>._query"
    elif framework=="Strawberry":
        mutation_transaction_name = query_transaction_name = "strawberry.asgi:GraphQL.__call__"
    elif (framework == "Ariadne") and (is_wsgi_or_asgi == "wsgi"):
        mutation_transaction_name = query_transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif framework == "Ariadne":
        mutation_transaction_name = query_transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"

    _expected_mutation_operation_attributes = {
        "graphql.operation.name": "storage_add" if framework == "Strawberry" else "GraphQL Operation",    # Otel changes it to whatever was in the path if there is no name
    }
    _expected_mutation_resolver_attributes = {
        "graphql.field.parentType": "Mutation",
        "graphql.field.path": "storage_add",
    }
    _expected_query_operation_attributes = {
        "graphql.operation.name": "storage" if framework == "Strawberry" else "GraphQL Operation",     # Otel changes it to whatever was in the path if there is no name
    }
    _expected_query_resolver_attributes = {
        "graphql.field.parentType": "Query",
        "graphql.field.path": "storage",
    }

    @validate_span_events(exact_agents=_expected_mutation_resolver_attributes)
    @validate_span_events(exact_agents=_expected_mutation_operation_attributes)
    @validate_transaction_metrics(
        mutation_transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _mutation():
        query = 'mutation { storage_add(string: "abc") }'
        response = target_application(query)
        assert response["storage_add"] == "abc" or response["storage_add"]["string"] == "abc"

    @validate_span_events(exact_agents={**_expected_query_operation_attributes, **_expected_query_resolver_attributes})
    @validate_transaction_metrics(
        query_transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _query():
        response = target_application("query { storage }")
        assert response["storage"] == ["abc"]

    _mutation()
    _query()


@pytest.mark.parametrize("middleware", example_middleware)
@dt_enabled
def test_middleware(target_application, middleware):
    _, target_application, is_wsgi_or_asgi, schema_type = target_application

    if not is_wsgi_or_asgi:
        transaction_name = "hybridagent_graphql.test_application:test_middleware.<locals>._test"
    elif is_wsgi_or_asgi == "wsgi":
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif is_wsgi_or_asgi == "asgi":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__" 
        
    name = f"{middleware.__module__}:{middleware.__name__}"
    if "async" in name:
        if schema_type != "async":
            pytest.skip("Async middleware not supported in sync applications.")

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        response = target_application("{ hello }", middleware=[middleware])
        assert response["hello"] == "Hello!"

    _test()


# NOTE: For OpenTelemetry, this will NOT capture an error because
# the operation does not run within a context manager (and the
# error can only be implicitly captured if it is run within the
# context of a context manager).
@pytest.mark.parametrize("middleware", error_middleware)
@dt_enabled
def test_exception_in_middleware(target_application, middleware):
    framework, target_application, is_wsgi_or_asgi, schema_type = target_application
    query = "query MyQuery { error_middleware }"
    field = "error_middleware"

    if not is_wsgi_or_asgi:
        transaction_name = "hybridagent_graphql.test_application:test_exception_in_middleware.<locals>._test"
    elif is_wsgi_or_asgi == "wsgi":
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif is_wsgi_or_asgi == "asgi":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"
        
    if "async" in transaction_name:
        if schema_type != "async":
            pytest.skip("Async middleware not supported in sync applications.")

    # Attributes
    _expected_exception_resolver_attributes = {
        "graphql.field.parentType": "Query",
        "graphql.field.path": field,
    }
    _expected_exception_operation_attributes = {
        "graphql.operation.name": "MyQuery",
    }

    if framework == "Strawberry":
        _expected_exception_operation_attributes["graphql.operation.query"] = query

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        target_application(query, middleware=[middleware])

    _test()


@pytest.mark.parametrize("field", ("error", "error_non_null"))
@dt_enabled
def test_exception_in_resolver(target_application, field):
    framework, target_application, is_wsgi_or_asgi, _ = target_application
    query = f"query MyQuery {{ {field} }}"

    if not is_wsgi_or_asgi:
        transaction_name = f"hybridagent_graphql.test_application:test_exception_in_resolver.<locals>._test"
    elif framework == "Strawberry":
        transaction_name = "strawberry.asgi:GraphQL.__call__"
    elif (framework == "Ariadne") and (is_wsgi_or_asgi == "wsgi"):
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif framework == "Ariadne":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"

    # Attributes
    _expected_exception_resolver_attributes = {

        "graphql.field.parentType": "Query",
        "graphql.field.path": field,
    }
    _expected_exception_operation_attributes = {
        "graphql.operation.name": "MyQuery",
    }
    
    if framework == "Strawberry":
        _expected_exception_operation_attributes["graphql.operation.query"] = query

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        target_application(query)

    _test()


# NOTE: For OpenTelemetry, this will NOT capture an error because
# the operation does not run within a context manager (and the
# error can only be implicitly captured if it is run within the
# context of a context manager).
@dt_enabled
@pytest.mark.parametrize(
    "query,exc_class",
    [
        ("query MyQuery { error_missing_field }", "GraphQLError"),
        ("{ syntax_error ", "graphql.error.syntax_error:GraphQLSyntaxError"),
    ],
)
def test_exception_in_validation(target_application, query, exc_class):
    framework, target_application, is_wsgi_or_asgi, _ = target_application
    
    if not is_wsgi_or_asgi:
        transaction_name = "hybridagent_graphql.test_application:test_exception_in_validation.<locals>._test"
    elif framework=="Strawberry":
        transaction_name = "strawberry.asgi:GraphQL.__call__"
    elif (framework=="Ariadne") and (is_wsgi_or_asgi == "wsgi"):
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif framework=="Ariadne":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"

    # Import path differs between versions
    if exc_class == "GraphQLError":
        from graphql.error import GraphQLError

        exc_class = callable_name(GraphQLError)

    # Attributes
    _expected_exception_operation_attributes = {
        "graphql.operation.query": query,
    }

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @conditional_decorator(
        condition=(framework == "Strawberry"),
        decorator=validate_span_events(exact_agents=_expected_exception_operation_attributes)
    )
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        target_application(query)

    _test()


@dt_enabled
def test_operation_metrics_and_attrs(target_application):
    framework, target_application, is_wsgi_or_asgi, _ = target_application
    operation_attrs = {"graphql.operation.name": "MyQuery"}
    
    if not is_wsgi_or_asgi:
        transaction_name = f"hybridagent_graphql.test_application:test_operation_metrics_and_attrs.<locals>._test"
    elif framework=="Strawberry":
        transaction_name = "strawberry.asgi:GraphQL.__call__"
    elif (framework=="Ariadne") and (is_wsgi_or_asgi == "wsgi"):
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif framework=="Ariadne":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @validate_span_events(exact_agents=operation_attrs)
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        target_application("query MyQuery { library(index: 0) { branch, book { id, name } } }")

    _test()


@dt_enabled
def test_field_resolver_metrics_and_attrs(target_application):
    framework, target_application, is_wsgi_or_asgi, _ = target_application

    if not is_wsgi_or_asgi:
        transaction_name = f"hybridagent_graphql.test_application:test_field_resolver_metrics_and_attrs.<locals>._test"
    elif framework=="Strawberry":
        transaction_name = "strawberry.asgi:GraphQL.__call__"
    elif (framework=="Ariadne") and (is_wsgi_or_asgi == "wsgi"):
        transaction_name = "ariadne.wsgi:GraphQL.__call__"
    elif framework=="Ariadne":
        transaction_name = "ariadne.asgi.graphql:GraphQL.__call__"

    graphql_attrs = {
        "graphql.field.parentType": "Query",
        "graphql.field.path": "hello",
    }

    @validate_transaction_metrics(
        transaction_name,
        background_task=not is_wsgi_or_asgi,
    )
    @validate_span_events(exact_agents=graphql_attrs)
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        response = target_application("{ hello }")
        assert response["hello"] == "Hello!"

    _test()


_test_queries = [
    ("{ hello }", "{ hello }", None),  # Basic query extraction
    ("{ error }", "{ error }", None),  # Extract query on field error
    (to_graphql_source("{ hello }"), "{ hello }", None),  # Extract query from Source objects
    ("{ library(index: 0) { branch } }", "{ library(index: ?) { branch } }", "index"),  # Integers
    ('{ echo(echo: "123") }', "{ echo(echo: ?) }", "echo"),  # Strings with numerics
    ('{ echo(echo: "test") }', "{ echo(echo: ?) }", "echo"),  # Strings
    ('{ TestEcho: echo(echo: "test") }', "{ TestEcho: echo(echo: ?) }", "echo"),  # Aliases
    ('{ TestEcho: echo(echo: "test") }', "{ TestEcho: echo(echo: ?) }", "echo"),  # Variables
    (  # Fragments
        '{ ...MyFragment } fragment MyFragment on Query { echo(echo: "test") },',
        "{ ...MyFragment } fragment MyFragment on Query { echo(echo: ?) },",
        "echo",
    ),
]


@dt_enabled
@pytest.mark.parametrize("query,obfuscated,key", _test_queries)
def test_query_obfuscation(target_application, query, obfuscated, key):
    framework, target_application, is_wsgi_or_asgi, _ = target_application

    if framework == "Ariadne":
        graphql_attrs = {}
        user_attrs = {f"graphql.arg[{key}]": "?"} if key else {}
    elif framework == "Strawberry":
        graphql_attrs = {"graphql.operation.query": obfuscated}
        user_attrs = {f"graphql.param.{key}": "?"} if key else {}
        
    if callable(query):
        if framework != "GraphQL":
            pytest.skip("Source query objects not tested outside of graphql-core")
        query = query()

    @conditional_decorator(decorator=validate_span_events(exact_agents=graphql_attrs), condition=bool(graphql_attrs))
    @conditional_decorator(decorator=validate_span_events(exact_users=user_attrs), condition=bool(user_attrs))
    @conditional_decorator(decorator=background_task(), condition=(not is_wsgi_or_asgi))
    def _test():
        target_application(query)

    _test()


# NOTE: Opentelemetry has their own transaction naming convention.
# The deepest unique path does not need to be tested here.

# NOTE: Opentelemetry does not capture the field name, so the 
# `capture_introspection_setting` is a no-op