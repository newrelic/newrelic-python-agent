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
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from framework_graphql.test_application_async import error_middleware_async, example_middleware_async
from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version

graphql_version = get_package_version("graphql-core")


def conditional_decorator(decorator, condition):
    def _conditional_decorator(func):
        if not condition:
            return func
        return decorator(func)

    return _conditional_decorator


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
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application

    def _test():
        response = target_application("{ __schema { types { name } } }")

    _test()


example_middleware = [example_middleware]
error_middleware = [error_middleware]

example_middleware.append(example_middleware_async)
error_middleware.append(error_middleware_async)

_runtime_error_name = callable_name(RuntimeError)
_test_runtime_error = [(_runtime_error_name, "Runtime Error!")]


def _graphql_base_rollup_metrics(framework, version, background_task=True):
    graphql_version = get_package_version("graphql-core")

    metrics = [(f"Python/Framework/GraphQL/{graphql_version}", 1), ("GraphQL/all", 1), (f"GraphQL/{framework}/all", 1)]
    if background_task:
        metrics.extend([("GraphQL/allOther", 1), (f"GraphQL/{framework}/allOther", 1)])
    else:
        metrics.extend([("GraphQL/allWeb", 1), (f"GraphQL/{framework}/allWeb", 1)])

    if framework != "GraphQL":
        metrics.append((f"Python/Framework/{framework}/{version}", 1))

    return metrics


def test_basic(target_application):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        rollup_metrics=_graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application("{ hello }")
        assert response["hello"] == "Hello!"

    _test()


@dt_enabled
def test_query_and_mutation(target_application):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application

    mutation_path = "storage_add" if framework != "Graphene" else "storage_add.string"
    type_annotation = "!" if framework == "Strawberry" else ""

    _test_mutation_scoped_metrics = [
        (f"GraphQL/resolve/{framework}/storage_add", 1),
        (f"GraphQL/operation/{framework}/mutation/<anonymous>/{mutation_path}", 1),
    ]
    _test_query_scoped_metrics = [
        (f"GraphQL/resolve/{framework}/storage", 1),
        (f"GraphQL/operation/{framework}/query/<anonymous>/storage", 1),
    ]
    _expected_mutation_operation_attributes = {
        "graphql.operation.type": "mutation",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_mutation_resolver_attributes = {
        "graphql.field.name": "storage_add",
        "graphql.field.parentType": "Mutation",
        "graphql.field.path": "storage_add",
        "graphql.field.returnType": ("String" if framework != "Graphene" else "StorageAdd") + type_annotation,
    }
    _expected_query_operation_attributes = {"graphql.operation.type": "query", "graphql.operation.name": "<anonymous>"}
    _expected_query_resolver_attributes = {
        "graphql.field.name": "storage",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "storage",
        "graphql.field.returnType": f"[String{type_annotation}]{type_annotation}",
    }

    @validate_code_level_metrics(f"framework_{framework.lower()}._target_schema_{schema_type}", "resolve_storage_add")
    @validate_span_events(exact_agents=_expected_mutation_operation_attributes)
    @validate_span_events(exact_agents=_expected_mutation_resolver_attributes)
    @validate_transaction_metrics(
        f"mutation/<anonymous>/{mutation_path}",
        "GraphQL",
        scoped_metrics=_test_mutation_scoped_metrics,
        rollup_metrics=_test_mutation_scoped_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @conditional_decorator(background_task(), is_bg)
    def _mutation():
        if framework == "Graphene":
            query = 'mutation { storage_add(string: "abc") { string } }'
        else:
            query = 'mutation { storage_add(string: "abc") }'
        response = target_application(query)
        assert response["storage_add"] == "abc" or response["storage_add"]["string"] == "abc"

    @validate_code_level_metrics(f"framework_{framework.lower()}._target_schema_{schema_type}", "resolve_storage")
    @validate_span_events(exact_agents=_expected_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_query_resolver_attributes)
    @validate_transaction_metrics(
        "query/<anonymous>/storage",
        "GraphQL",
        scoped_metrics=_test_query_scoped_metrics,
        rollup_metrics=_test_query_scoped_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @conditional_decorator(background_task(), is_bg)
    def _query():
        response = target_application("query { storage }")
        assert response["storage"] == ["abc"]

    _mutation()
    _query()


@pytest.mark.parametrize("middleware", example_middleware)
@dt_enabled
def test_middleware(target_application, middleware):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application

    name = f"{middleware.__module__}:{middleware.__name__}"
    if "async" in name:
        if schema_type != "async":
            pytest.skip("Async middleware not supported in sync applications.")

    _test_middleware_metrics = [
        (f"GraphQL/operation/{framework}/query/<anonymous>/hello", 1),
        (f"GraphQL/resolve/{framework}/hello", 1),
        (f"Function/{name}", 1),
    ]

    # Span count 5: Transaction, Operation, Middleware, and 1 Resolver and Resolver Function
    span_count = 5 + extra_spans

    @validate_code_level_metrics(*name.split(":"))
    @validate_code_level_metrics(f"framework_{framework.lower()}._target_schema_{schema_type}", "resolve_hello")
    @validate_span_events(count=span_count)
    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=_test_middleware_metrics,
        rollup_metrics=_test_middleware_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application("{ hello }", middleware=[middleware])
        assert response["hello"] == "Hello!"

    _test()


@pytest.mark.parametrize("middleware", error_middleware)
@dt_enabled
def test_exception_in_middleware(target_application, middleware):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    query = "query MyQuery { error_middleware }"
    field = "error_middleware"

    name = f"{middleware.__module__}:{middleware.__name__}"
    if "async" in name:
        if schema_type != "async":
            pytest.skip("Async middleware not supported in sync applications.")

    # Metrics
    _test_exception_scoped_metrics = [
        (f"GraphQL/operation/{framework}/query/MyQuery/{field}", 1),
        (f"GraphQL/resolve/{framework}/{field}", 1),
        (f"Function/{name}", 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        (f"Errors/all{'Other' if is_bg else 'Web'}", 1),
        (f"Errors/{'Other' if is_bg else 'Web'}Transaction/GraphQL/{name}", 1),
    ] + _test_exception_scoped_metrics

    # Attributes
    _expected_exception_resolver_attributes = {
        "graphql.field.name": field,
        "graphql.field.parentType": "Query",
        "graphql.field.path": field,
        "graphql.field.returnType": "String",
    }
    _expected_exception_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "MyQuery",
        "graphql.operation.query": query,
    }

    @validate_transaction_metrics(
        name,
        "GraphQL",
        scoped_metrics=_test_exception_scoped_metrics,
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application(query, middleware=[middleware])

    _test()


@pytest.mark.parametrize("field", ("error", "error_non_null"))
@dt_enabled
def test_exception_in_resolver(target_application, field):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    query = f"query MyQuery {{ {field} }}"

    txn_name = f"framework_{framework.lower()}._target_schema_{schema_type}:resolve_error"

    # Metrics
    _test_exception_scoped_metrics = [
        (f"GraphQL/operation/{framework}/query/MyQuery/{field}", 1),
        (f"GraphQL/resolve/{framework}/{field}", 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        (f"Errors/all{'Other' if is_bg else 'Web'}", 1),
        (f"Errors/{'Other' if is_bg else 'Web'}Transaction/GraphQL/{txn_name}", 1),
    ] + _test_exception_scoped_metrics

    # Attributes
    _expected_exception_resolver_attributes = {
        "graphql.field.name": field,
        "graphql.field.parentType": "Query",
        "graphql.field.path": field,
        "graphql.field.returnType": "String!" if "non_null" in field else "String",
    }
    _expected_exception_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "MyQuery",
        "graphql.operation.query": query,
    }

    @validate_transaction_metrics(
        txn_name,
        "GraphQL",
        scoped_metrics=_test_exception_scoped_metrics,
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application(query)

    _test()


@dt_enabled
@pytest.mark.parametrize(
    "query,exc_class",
    [
        ("query MyQuery { error_missing_field }", "GraphQLError"),
        ("{ syntax_error ", "graphql.error.syntax_error:GraphQLSyntaxError"),
    ],
)
def test_exception_in_validation(target_application, query, exc_class):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    if "syntax" in query:
        txn_name = "graphql.language.parser:parse"
    else:
        txn_name = "graphql.validation.validate:validate"

    # Import path differs between versions
    if exc_class == "GraphQLError":
        from graphql.error import GraphQLError

        exc_class = callable_name(GraphQLError)

    _test_exception_scoped_metrics = [(f"GraphQL/operation/{framework}/<unknown>/<anonymous>/<unknown>", 1)]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        (f"Errors/all{'Other' if is_bg else 'Web'}", 1),
        (f"Errors/{'Other' if is_bg else 'Web'}Transaction/GraphQL/{txn_name}", 1),
    ] + _test_exception_scoped_metrics

    # Attributes
    _expected_exception_operation_attributes = {
        "graphql.operation.type": "<unknown>",
        "graphql.operation.name": "<anonymous>",
        "graphql.operation.query": query,
    }

    @validate_transaction_metrics(
        txn_name,
        "GraphQL",
        scoped_metrics=_test_exception_scoped_metrics,
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_transaction_errors(errors=[exc_class])
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application(query)

    _test()


@dt_enabled
def test_operation_metrics_and_attrs(target_application):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    operation_metrics = [(f"GraphQL/operation/{framework}/query/MyQuery/library", 1)]
    operation_attrs = {"graphql.operation.type": "query", "graphql.operation.name": "MyQuery"}

    # Span count 16: Transaction, Operation, and 7 Resolvers and Resolver functions
    # library, library.name, library.book
    # library.book.name and library.book.id for each book resolved (in this case 2)
    span_count = 16 + extra_spans  # WSGI may add 4 spans, other frameworks may add other amounts

    @validate_transaction_metrics(
        "query/MyQuery/library",
        "GraphQL",
        scoped_metrics=operation_metrics,
        rollup_metrics=operation_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @validate_span_events(count=span_count)
    @validate_span_events(exact_agents=operation_attrs)
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application("query MyQuery { library(index: 0) { branch, book { id, name } } }")

    _test()


@dt_enabled
def test_field_resolver_metrics_and_attrs(target_application):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    field_resolver_metrics = [(f"GraphQL/resolve/{framework}/hello", 1)]

    type_annotation = "!" if framework == "Strawberry" else ""
    graphql_attrs = {
        "graphql.field.name": "hello",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "hello",
        "graphql.field.returnType": f"String{type_annotation}",
    }

    # Span count 4: Transaction, Operation, and 1 Resolver and Resolver function
    span_count = 4 + extra_spans  # WSGI may add 4 spans, other frameworks may add other amounts

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=field_resolver_metrics,
        rollup_metrics=field_resolver_metrics + _graphql_base_rollup_metrics(framework, version, is_bg),
        background_task=is_bg,
    )
    @validate_span_events(count=span_count)
    @validate_span_events(exact_agents=graphql_attrs)
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application("{ hello }")
        assert response["hello"] == "Hello!"

    _test()


_test_queries = [
    ("{ hello }", "{ hello }"),  # Basic query extraction
    ("{ error }", "{ error }"),  # Extract query on field error
    (to_graphql_source("{ hello }"), "{ hello }"),  # Extract query from Source objects
    ("{ library(index: 0) { branch } }", "{ library(index: ?) { branch } }"),  # Integers
    ('{ echo(echo: "123") }', "{ echo(echo: ?) }"),  # Strings with numerics
    ('{ echo(echo: "test") }', "{ echo(echo: ?) }"),  # Strings
    ('{ TestEcho: echo(echo: "test") }', "{ TestEcho: echo(echo: ?) }"),  # Aliases
    ('{ TestEcho: echo(echo: "test") }', "{ TestEcho: echo(echo: ?) }"),  # Variables
    (  # Fragments
        '{ ...MyFragment } fragment MyFragment on Query { echo(echo: "test") }',
        "{ ...MyFragment } fragment MyFragment on Query { echo(echo: ?) }",
    ),
]


@dt_enabled
@pytest.mark.parametrize("query,obfuscated", _test_queries)
def test_query_obfuscation(target_application, query, obfuscated):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    graphql_attrs = {"graphql.operation.query": obfuscated}

    if callable(query):
        if framework != "GraphQL":
            pytest.skip("Source query objects not tested outside of graphql-core")
        query = query()

    @validate_span_events(exact_agents=graphql_attrs)
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application(query)

    _test()


_test_queries = [
    ("{ hello }", "/hello"),  # Basic query
    ("{ error }", "/error"),  # Extract deepest path on field error
    ('{ echo(echo: "test") }', "/echo"),  # Fields with arguments
    ("{ library(index: 0) { branch, book { isbn branch } } }", "/library"),  # Complex Example, 1 level
    (
        "{ library(index: 0) { book { author { first_name }} } }",
        "/library.book.author.first_name",
    ),  # Complex Example, 2 levels
    ("{ library(index: 0) { id, book { name } } }", "/library.book.name"),  # Filtering
    ('{ TestEcho: echo(echo: "test") }', "/echo"),  # Aliases
    ('{ search(contains: "A") { __typename ... on Book { name } } }', "/search<Book>.name"),  # InlineFragment
    ('{ hello echo(echo: "test") }', ""),  # Multiple root selections. (need to decide on final behavior)
    # FragmentSpread
    (
        "{ library(index: 0) { book { ...MyFragment } } } fragment MyFragment on Book { name id }",  # Fragment filtering
        "/library.book.name",
    ),
    (
        "{ library(index: 0) { book { ...MyFragment } } } fragment MyFragment on Book { author { first_name } }",
        "/library.book.author.first_name",
    ),
    (
        "{ library(index: 0) { book { ...MyFragment } magazine { ...MagFragment } } } fragment MyFragment on Book { author { first_name } } fragment MagFragment on Magazine { name }",
        "/library",
    ),
]


@dt_enabled
@pytest.mark.parametrize("query,expected_path", _test_queries)
def test_deepest_unique_path(target_application, query, expected_path):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    if expected_path == "/error":
        txn_name = f"framework_{framework.lower()}._target_schema_{schema_type}:resolve_error"
    else:
        txn_name = f"query/<anonymous>{expected_path}"

    @validate_transaction_metrics(txn_name, "GraphQL", background_task=is_bg)
    @conditional_decorator(background_task(), is_bg)
    def _test():
        response = target_application(query)

    _test()


@pytest.mark.parametrize("capture_introspection_setting", (True, False))
def test_introspection_transactions(target_application, capture_introspection_setting):
    framework, version, target_application, is_bg, schema_type, extra_spans = target_application
    txn_ct = 1 if capture_introspection_setting else 0

    @override_application_settings(
        {"instrumentation.graphql.capture_introspection_queries": capture_introspection_setting}
    )
    @validate_transaction_count(txn_ct)
    @background_task()
    def _test():
        response = target_application("{ __schema { types { name } } }")

    _test()
