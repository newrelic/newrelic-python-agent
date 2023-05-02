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

import importlib

import pytest
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)

from newrelic.common.object_names import callable_name


@pytest.fixture(scope="session")
def is_graphql_2():
    from graphql import __version__ as version

    major_version = int(version.split(".")[0])
    return major_version == 2


@pytest.fixture(scope="session", params=("Sanic", "Flask"))
def target_application(request):
    import _test_graphql

    framework = request.param
    version = importlib.import_module(framework.lower()).__version__

    return framework, version, _test_graphql.target_application[framework]


def example_middleware(next, root, info, **args):  # pylint: disable=W0622
    return_value = next(root, info, **args)
    return return_value


def error_middleware(next, root, info, **args):  # pylint: disable=W0622
    raise RuntimeError("Runtime Error!")


_runtime_error_name = callable_name(RuntimeError)
_test_runtime_error = [(_runtime_error_name, "Runtime Error!")]
_graphql_base_rollup_metrics = [
    ("GraphQL/all", 1),
    ("GraphQL/allWeb", 1),
    ("GraphQL/GraphQLServer/all", 1),
    ("GraphQL/GraphQLServer/allWeb", 1),
]
_view_metrics = {
    "Sanic": "Function/graphql_server.sanic.graphqlview:GraphQLView.post",
    "Flask": "Function/graphql_server.flask.graphqlview:graphql",
}


def test_basic(target_application):
    framework, version, target_application = target_application
    from graphql import __version__ as graphql_version
    from graphql_server import __version__ as graphql_server_version

    FRAMEWORK_METRICS = [
        ("Python/Framework/GraphQL/%s" % graphql_version, 1),
        ("Python/Framework/GraphQLServer/%s" % graphql_server_version, 1),
        ("Python/Framework/%s/%s" % (framework, version), 1),
    ]

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        rollup_metrics=_graphql_base_rollup_metrics + FRAMEWORK_METRICS,
    )
    def _test():
        response = target_application("{ hello }")

    _test()


@dt_enabled
def test_query_and_mutation(target_application):
    framework, version, target_application = target_application
    from graphql import __version__ as graphql_version
    from graphql_server import __version__ as graphql_server_version

    FRAMEWORK_METRICS = [
        ("Python/Framework/GraphQL/%s" % graphql_version, 1),
        ("Python/Framework/GraphQLServer/%s" % graphql_server_version, 1),
        ("Python/Framework/%s/%s" % (framework, version), 1),
    ]
    _test_query_scoped_metrics = [
        ("GraphQL/resolve/GraphQLServer/storage", 1),
        ("GraphQL/operation/GraphQLServer/query/<anonymous>/storage", 1),
        (_view_metrics[framework], 1),
    ]
    _test_query_unscoped_metrics = [
        ("GraphQL/all", 1),
        ("GraphQL/GraphQLServer/all", 1),
        ("GraphQL/allWeb", 1),
        ("GraphQL/GraphQLServer/allWeb", 1),
    ] + _test_query_scoped_metrics

    _test_mutation_scoped_metrics = [
        ("GraphQL/resolve/GraphQLServer/storage_add", 1),
        ("GraphQL/operation/GraphQLServer/mutation/<anonymous>/storage_add", 1),
        (_view_metrics[framework], 1),
    ]
    _test_mutation_unscoped_metrics = [
        ("GraphQL/all", 1),
        ("GraphQL/GraphQLServer/all", 1),
        ("GraphQL/allWeb", 1),
        ("GraphQL/GraphQLServer/allWeb", 1),
    ] + _test_mutation_scoped_metrics

    _expected_mutation_operation_attributes = {
        "graphql.operation.type": "mutation",
        "graphql.operation.name": "<anonymous>",
        "graphql.operation.query": "mutation { storage_add(string: ?) }",
    }
    _expected_mutation_resolver_attributes = {
        "graphql.field.name": "storage_add",
        "graphql.field.parentType": "Mutation",
        "graphql.field.path": "storage_add",
        "graphql.field.returnType": "String",
    }
    _expected_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "<anonymous>",
        "graphql.operation.query": "query { storage }",
    }
    _expected_query_resolver_attributes = {
        "graphql.field.name": "storage",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "storage",
        "graphql.field.returnType": "[String]",
    }

    def _test():
        @validate_transaction_metrics(
            "mutation/<anonymous>/storage_add",
            "GraphQL",
            scoped_metrics=_test_mutation_scoped_metrics,
            rollup_metrics=_test_mutation_unscoped_metrics + FRAMEWORK_METRICS,
        )
        @validate_span_events(exact_agents=_expected_mutation_operation_attributes)
        @validate_span_events(exact_agents=_expected_mutation_resolver_attributes)
        def _mutation():
            return target_application('mutation { storage_add(string: "abc") }')

        @validate_transaction_metrics(
            "query/<anonymous>/storage",
            "GraphQL",
            scoped_metrics=_test_query_scoped_metrics,
            rollup_metrics=_test_query_unscoped_metrics + FRAMEWORK_METRICS,
        )
        @validate_span_events(exact_agents=_expected_query_operation_attributes)
        @validate_span_events(exact_agents=_expected_query_resolver_attributes)
        def _query():
            return target_application("query { storage }")

        response = _mutation()
        response = _query()

        # These are separate assertions because pypy stores 'abc' as a unicode string while other Python versions do not
        assert "storage" in str(response.body.decode("utf-8"))
        assert "abc" in str(response.body.decode("utf-8"))

    _test()


@dt_enabled
def test_middleware(target_application):
    framework, version, target_application = target_application
    _test_middleware_metrics = [
        ("GraphQL/operation/GraphQLServer/query/<anonymous>/hello", 1),
        ("GraphQL/resolve/GraphQLServer/hello", 1),
        ("Function/test_graphql:example_middleware", 1),
    ]

    # Base span count 6: Transaction, View, Operation, Middleware, and 1 Resolver and Resolver function
    # For Flask, add 9 more for WSGI and framework related spans
    span_count = {"Flask": 15, "Sanic": 6}

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=_test_middleware_metrics,
        rollup_metrics=_test_middleware_metrics + _graphql_base_rollup_metrics,
    )
    @validate_span_events(count=span_count[framework])
    def _test():
        response = target_application("{ hello }", middleware=[example_middleware])

    _test()


@dt_enabled
def test_exception_in_middleware(target_application):
    framework, version, target_application = target_application
    query = "query MyQuery { error_middleware }"
    field = "error_middleware"

    # Metrics
    _test_exception_scoped_metrics = [
        ("GraphQL/operation/GraphQLServer/query/MyQuery/%s" % field, 1),
        ("GraphQL/resolve/GraphQLServer/%s" % field, 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        ("Errors/allWeb", 1),
        ("Errors/WebTransaction/GraphQL/test_graphql:error_middleware", 1),
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
        "test_graphql:error_middleware",
        "GraphQL",
        scoped_metrics=_test_exception_scoped_metrics,
        rollup_metrics=_test_exception_rollup_metrics + _graphql_base_rollup_metrics,
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
    def _test():
        response = target_application(query, middleware=[error_middleware])

    _test()


@pytest.mark.parametrize("field", ("error", "error_non_null"))
@dt_enabled
def test_exception_in_resolver(target_application, field):
    framework, version, target_application = target_application
    query = "query MyQuery { %s }" % field

    txn_name = "framework_graphql._target_application:resolve_error"

    # Metrics
    _test_exception_scoped_metrics = [
        ("GraphQL/operation/GraphQLServer/query/MyQuery/%s" % field, 1),
        ("GraphQL/resolve/GraphQLServer/%s" % field, 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        ("Errors/allWeb", 1),
        ("Errors/WebTransaction/GraphQL/%s" % txn_name, 1),
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
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_span_events(exact_agents=_expected_exception_resolver_attributes)
    @validate_transaction_errors(errors=_test_runtime_error)
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
def test_exception_in_validation(target_application, is_graphql_2, query, exc_class):
    framework, version, target_application = target_application
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
        ("GraphQL/operation/GraphQLServer/<unknown>/<anonymous>/<unknown>", 1),
    ]
    _test_exception_rollup_metrics = [
        ("Errors/all", 1),
        ("Errors/allWeb", 1),
        ("Errors/WebTransaction/GraphQL/%s" % txn_name, 1),
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
    )
    @validate_span_events(exact_agents=_expected_exception_operation_attributes)
    @validate_transaction_errors(errors=[exc_class])
    def _test():
        response = target_application(query)

    _test()


@dt_enabled
def test_operation_metrics_and_attrs(target_application):
    framework, version, target_application = target_application
    operation_metrics = [("GraphQL/operation/GraphQLServer/query/MyQuery/library", 1)]
    operation_attrs = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "MyQuery",
    }

    # Base span count 17: Transaction, View, Operation, and 7 Resolvers and Resolver functions
    # library, library.name, library.book
    # library.book.name and library.book.id for each book resolved (in this case 2)
    # For Flask, add 9 more for WSGI and framework related spans
    span_count = {"Flask": 26, "Sanic": 17}

    @validate_transaction_metrics(
        "query/MyQuery/library",
        "GraphQL",
        scoped_metrics=operation_metrics,
        rollup_metrics=operation_metrics + _graphql_base_rollup_metrics,
    )
    @validate_span_events(count=span_count[framework])
    @validate_span_events(exact_agents=operation_attrs)
    def _test():
        response = target_application("query MyQuery { library(index: 0) { branch, book { id, name } } }")

    _test()


@dt_enabled
def test_field_resolver_metrics_and_attrs(target_application):
    framework, version, target_application = target_application
    field_resolver_metrics = [("GraphQL/resolve/GraphQLServer/hello", 1)]
    graphql_attrs = {
        "graphql.field.name": "hello",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "hello",
        "graphql.field.returnType": "String",
    }

    # Base span count 5: Transaction, View, Operation, and 1 Resolver and Resolver function
    # For Flask, add 9 more for WSGI and framework related spans
    span_count = {"Flask": 14, "Sanic": 5}

    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=field_resolver_metrics,
        rollup_metrics=field_resolver_metrics + _graphql_base_rollup_metrics,
    )
    @validate_span_events(count=span_count[framework])
    @validate_span_events(exact_agents=graphql_attrs)
    def _test():
        response = target_application("{ hello }")
        assert "Hello!" in response.body.decode("utf-8")

    _test()


_test_queries = [
    ("{ hello }", "{ hello }"),  # Basic query extraction
    ("{ error }", "{ error }"),  # Extract query on field error
    (
        "{ library(index: 0) { branch } }",
        "{ library(index: ?) { branch } }",
    ),  # Integers
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
    framework, version, target_application = target_application
    graphql_attrs = {"graphql.operation.query": obfuscated}

    if callable(query):
        query = query()

    @validate_span_events(exact_agents=graphql_attrs)
    def _test():
        response = target_application(query)

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
def test_deepest_unique_path(target_application, query, expected_path):
    framework, version, target_application = target_application
    if expected_path == "/error":
        txn_name = "framework_graphql._target_application:resolve_error"
    else:
        txn_name = "query/<anonymous>%s" % expected_path

    @validate_transaction_metrics(
        txn_name,
        "GraphQL",
    )
    def _test():
        response = target_application(query)

    _test()


@validate_transaction_count(0)
def test_ignored_introspection_transactions(target_application):
    framework, version, target_application = target_application
    response = target_application("{ __schema { types { name } } }")
