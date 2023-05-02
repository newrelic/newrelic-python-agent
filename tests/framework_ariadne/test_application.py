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
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version_tuple


@pytest.fixture(scope="session")
def is_graphql_2():
    from graphql import __version__ as version

    major_version = int(version.split(".")[0])
    return major_version == 2


@pytest.fixture(scope="session")
def graphql_run():
    """Wrapper function to simulate framework_graphql test behavior."""

    def execute(schema, query, *args, **kwargs):
        from ariadne import graphql_sync

        return graphql_sync(schema, {"query": query}, *args, **kwargs)

    return execute


def to_graphql_source(query):
    def delay_import():
        try:
            from graphql import Source
        except ImportError:
            # Fallback if Source is not implemented
            return query

        from graphql import __version__ as version

        # For graphql2, Source objects aren't acceptable input
        major_version = int(version.split(".")[0])
        if major_version == 2:
            return query

        return Source(query)

    return delay_import


def example_middleware(next, root, info, **args):  # pylint: disable=W0622
    return_value = next(root, info, **args)
    return return_value


def error_middleware(next, root, info, **args):  # pylint: disable=W0622
    raise RuntimeError("Runtime Error!")


_runtime_error_name = callable_name(RuntimeError)
_test_runtime_error = [(_runtime_error_name, "Runtime Error!")]
_graphql_base_rollup_metrics = [
    ("OtherTransaction/all", 1),
    ("GraphQL/all", 1),
    ("GraphQL/allOther", 1),
    ("GraphQL/Ariadne/all", 1),
    ("GraphQL/Ariadne/allOther", 1),
]


def test_basic(app, graphql_run):
    from graphql import __version__ as version

    FRAMEWORK_METRICS = [
        ("Python/Framework/Ariadne/None", 1),
        ("Python/Framework/GraphQL/%s" % version, 1),
    ]

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        rollup_metrics=_graphql_base_rollup_metrics + FRAMEWORK_METRICS,
        background_task=True,
    )
    @background_task()
    def _test():
        ok, response = graphql_run(app, "{ hello }")
        assert ok and not response.get("errors")

    _test()


@dt_enabled
def test_query_and_mutation(app, graphql_run):
    from graphql import __version__ as version

    FRAMEWORK_METRICS = [
        ("Python/Framework/Ariadne/None", 1),
        ("Python/Framework/GraphQL/%s" % version, 1),
    ]
    _test_mutation_scoped_metrics = [
        ("GraphQL/resolve/Ariadne/storage", 1),
        ("GraphQL/resolve/Ariadne/storage_add", 1),
        ("GraphQL/operation/Ariadne/query/<anonymous>/storage", 1),
        ("GraphQL/operation/Ariadne/mutation/<anonymous>/storage_add.string", 1),
    ]
    _test_mutation_unscoped_metrics = [
        ("OtherTransaction/all", 1),
        ("GraphQL/all", 2),
        ("GraphQL/Ariadne/all", 2),
        ("GraphQL/allOther", 2),
        ("GraphQL/Ariadne/allOther", 2),
    ] + _test_mutation_scoped_metrics

    _expected_mutation_operation_attributes = {
        "graphql.operation.type": "mutation",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_mutation_resolver_attributes = {
        "graphql.field.name": "storage_add",
        "graphql.field.parentType": "Mutation",
        "graphql.field.path": "storage_add",
        "graphql.field.returnType": "StorageAdd",
    }
    _expected_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_query_resolver_attributes = {
        "graphql.field.name": "storage",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "storage",
        "graphql.field.returnType": "[String]",
    }

    @validate_transaction_metrics(
        "query/<anonymous>/storage",
        "GraphQL",
        scoped_metrics=_test_mutation_scoped_metrics,
        rollup_metrics=_test_mutation_unscoped_metrics + FRAMEWORK_METRICS,
        background_task=True,
    )
    @validate_span_events(exact_agents=_expected_mutation_operation_attributes)
    @validate_span_events(exact_agents=_expected_mutation_resolver_attributes)
    @validate_span_events(exact_agents=_expected_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_query_resolver_attributes)
    @background_task()
    def _test():
        ok, response = graphql_run(app, 'mutation { storage_add(string: "abc") { string } }')
        assert ok and not response.get("errors")
        ok, response = graphql_run(app, "query { storage }")
        assert ok and not response.get("errors")

        # These are separate assertions because pypy stores 'abc' as a unicode string while other Python versions do not
        assert "storage" in str(response["data"])
        assert "abc" in str(response["data"])

    _test()


@dt_enabled
def test_middleware(app, graphql_run, is_graphql_2):
    _test_middleware_metrics = [
        ("GraphQL/operation/Ariadne/query/<anonymous>/hello", 1),
        ("GraphQL/resolve/Ariadne/hello", 1),
        ("Function/test_application:example_middleware", 1),
    ]

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=_test_middleware_metrics,
        rollup_metrics=_test_middleware_metrics + _graphql_base_rollup_metrics,
        background_task=True,
    )
    # Span count 5: Transaction, Operation, Middleware, and 1 Resolver and Resolver function
    @validate_span_events(count=5)
    @background_task()
    def _test():
        from graphql import MiddlewareManager

        middleware = (
            [example_middleware]
            if get_package_version_tuple("ariadne") >= (0, 18)
            else MiddlewareManager(example_middleware)
        )

        ok, response = graphql_run(app, "{ hello }", middleware=middleware)
        assert ok and not response.get("errors")
        assert "Hello!" in str(response["data"])

    _test()


@dt_enabled
def test_exception_in_middleware(app, graphql_run):
    query = "query MyQuery { hello }"
    field = "hello"

    # Metrics
    _test_exception_scoped_metrics = [
        ("GraphQL/operation/Ariadne/query/MyQuery/%s" % field, 1),
        ("GraphQL/resolve/Ariadne/%s" % field, 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        ("Errors/allOther", 1),
        ("Errors/OtherTransaction/GraphQL/test_application:error_middleware", 1),
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
        "test_application:error_middleware",
        "GraphQL",
        scoped_metrics=_test_exception_scoped_metrics,
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics,
        background_task=True,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
    @background_task()
    def _test():
        from graphql import MiddlewareManager

        middleware = (
            [error_middleware]
            if get_package_version_tuple("ariadne") >= (0, 18)
            else MiddlewareManager(error_middleware)
        )

        _, response = graphql_run(app, query, middleware=middleware)
        assert response["errors"]

    _test()


@pytest.mark.parametrize("field", ("error", "error_non_null"))
@dt_enabled
def test_exception_in_resolver(app, graphql_run, field):
    query = "query MyQuery { %s }" % field
    txn_name = "_target_application:resolve_error"

    # Metrics
    _test_exception_scoped_metrics = [
        ("GraphQL/operation/Ariadne/query/MyQuery/%s" % field, 1),
        ("GraphQL/resolve/Ariadne/%s" % field, 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        ("Errors/allOther", 1),
        ("Errors/OtherTransaction/GraphQL/%s" % txn_name, 1),
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
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics,
        background_task=True,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
    @background_task()
    def _test():
        _, response = graphql_run(app, query)
        assert response["errors"]

    _test()


@dt_enabled
@pytest.mark.parametrize(
    "query,exc_class",
    [
        ("query MyQuery { missing_field }", "GraphQLError"),
        ("{ syntax_error ", "graphql.error.syntax_error:GraphQLSyntaxError"),
    ],
)
def test_exception_in_validation(app, graphql_run, is_graphql_2, query, exc_class):
    if "syntax" in query:
        txn_name = "graphql.language.parser:parse"
    else:
        if is_graphql_2:
            txn_name = "graphql.validation.validation:validate"
        else:
            txn_name = "graphql.validation.validate:validate"

    # Import path differs between versions
    if exc_class == "GraphQLError":
        from graphql.error import GraphQLError

        exc_class = callable_name(GraphQLError)

    _test_exception_scoped_metrics = [
        ("GraphQL/operation/Ariadne/<unknown>/<anonymous>/<unknown>", 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        ("Errors/allOther", 1),
        ("Errors/OtherTransaction/GraphQL/%s" % txn_name, 1),
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
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics,
        background_task=True,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_transaction_errors(errors=[exc_class])
    @background_task()
    def _test():
        _, response = graphql_run(app, query)
        assert response["errors"]

    _test()


@dt_enabled
def test_operation_metrics_and_attrs(app, graphql_run):
    operation_metrics = [("GraphQL/operation/Ariadne/query/MyQuery/library", 1)]
    operation_attrs = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "MyQuery",
    }

    @validate_transaction_metrics(
        "query/MyQuery/library",
        "GraphQL",
        scoped_metrics=operation_metrics,
        rollup_metrics=operation_metrics + _graphql_base_rollup_metrics,
        background_task=True,
    )
    # Span count 16: Transaction, Operation, and 7 Resolvers and Resolver functions
    # library, library.name, library.book
    # library.book.name and library.book.id for each book resolved (in this case 2)
    @validate_span_events(count=16)
    @validate_span_events(exact_agents=operation_attrs)
    @background_task()
    def _test():
        ok, response = graphql_run(app, "query MyQuery { library(index: 0) { branch, book { id, name } } }")
        assert ok and not response.get("errors")

    _test()


@dt_enabled
def test_field_resolver_metrics_and_attrs(app, graphql_run):
    field_resolver_metrics = [("GraphQL/resolve/Ariadne/hello", 1)]
    graphql_attrs = {
        "graphql.field.name": "hello",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "hello",
        "graphql.field.returnType": "String",
    }

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=field_resolver_metrics,
        rollup_metrics=field_resolver_metrics + _graphql_base_rollup_metrics,
        background_task=True,
    )
    # Span count 4: Transaction, Operation, and 1 Resolver and Resolver function
    @validate_span_events(count=4)
    @validate_span_events(exact_agents=graphql_attrs)
    @background_task()
    def _test():
        ok, response = graphql_run(app, "{ hello }")
        assert ok and not response.get("errors")
        assert "Hello!" in str(response["data"])

    _test()


_test_queries = [
    ("{ hello }", "{ hello }"),  # Basic query extraction
    ("{ error }", "{ error }"),  # Extract query on field error
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
def test_query_obfuscation(app, graphql_run, query, obfuscated):
    graphql_attrs = {"graphql.operation.query": obfuscated}

    @validate_span_events(exact_agents=graphql_attrs)
    @background_task()
    def _test():
        ok, response = graphql_run(app, query)
        if not isinstance(query, str) or "error" not in query:
            assert ok and not response.get("errors")

    _test()


_test_queries = [
    ("{ hello }", "/hello"),  # Basic query
    ("{ error }", "/error"),  # Extract deepest path on field error
    ('{ echo(echo: "test") }', "/echo"),  # Fields with arguments
    (
        "{ library(index: 0) { branch, book { isbn branch } } }",
        "/library",
    ),  # Complex Example, 1 level
    (
        "{ library(index: 0) { book { author { first_name }} } }",
        "/library.book.author.first_name",
    ),  # Complex Example, 2 levels
    ("{ library(index: 0) { id, book { name } } }", "/library.book.name"),  # Filtering
    ('{ TestEcho: echo(echo: "test") }', "/echo"),  # Aliases
    (
        '{ search(contains: "A") { __typename ... on Book { name } } }',
        "/search<Book>.name",
    ),  # InlineFragment
    (
        '{ hello echo(echo: "test") }',
        "",
    ),  # Multiple root selections. (need to decide on final behavior)
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
def test_deepest_unique_path(app, graphql_run, query, expected_path):
    if expected_path == "/error":
        txn_name = "_target_application:resolve_error"
    else:
        txn_name = "query/<anonymous>%s" % expected_path

    @validate_transaction_metrics(
        txn_name,
        "GraphQL",
        background_task=True,
    )
    @background_task()
    def _test():
        ok, response = graphql_run(app, query)
        if "error" not in query:
            assert ok and not response.get("errors")

    _test()


@pytest.mark.parametrize("capture_introspection_setting", (True, False))
def test_introspection_transactions(app, graphql_run, capture_introspection_setting):
    txn_ct = 1 if capture_introspection_setting else 0

    @override_application_settings(
        {"instrumentation.graphql.capture_introspection_queries": capture_introspection_setting}
    )
    @validate_transaction_count(txn_ct)
    @background_task()
    def _test():
        ok, response = graphql_run(app, "{ __schema { types { name } } }")
        assert ok and not response.get("errors")

    _test()
