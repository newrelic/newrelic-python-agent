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
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.common.package_version_utils import get_package_version

GRAPHENE_DJANGO_VERSION = get_package_version("graphene-django")
GRAPHQL_VERSION = get_package_version("graphql-core")


_graphql_base_rollup_metrics = [
    (f"Python/Framework/GraphQL/{GRAPHQL_VERSION}", 1),
    ("GraphQL/all", 1),
    ("GraphQL/GrapheneDjango/all", 1),
    ("GraphQL/allWeb", 1),
    ("GraphQL/GrapheneDjango/allWeb", 1),
    (f"Python/Framework/GrapheneDjango/{GRAPHENE_DJANGO_VERSION}", 1),
]


# Query, Expected deepest unique path, Result
_test_queries = [
    ("{ hello }", "/hello", {"data": {"hello": "Hello!"}}),  # Basic query
    (
        "{ error }",
        "/error",
        {
            "errors": [{"message": "Runtime Error!", "locations": [{"line": 1, "column": 3}], "path": ["error"]}],
            "data": {"error": None},
        },
    ),  # Extract deepest path on field error
    ('{ echo(echo: "test") }', "/echo", {"data": {"echo": "test"}}),  # Fields with arguments
    (
        "{ library(index: 0) { branch, book { isbn branch } } }",
        "/library",
        {
            "data": {
                "library": {
                    "branch": "riverside",
                    "book": [
                        {"isbn": "a-fake-isbn", "branch": "riverside"},
                        {"isbn": "a-third-fake-isbn", "branch": "riverside"},
                    ],
                }
            }
        },
    ),  # Complex Example, 1 level
    (
        "{ library(index: 0) { book { author { first_name }} } }",
        "/library.book.author.first_name",
        {"data": {"library": {"book": [{"author": {"first_name": "New"}}, {"author": {"first_name": "Leslie"}}]}}},
    ),  # Complex Example, 2 levels
    (
        "{ library(index: 0) { book { name } } }",
        "/library.book.name",
        {"data": {"library": {"book": [{"name": "Python Agent: The Book"}, {"name": "[Redacted]"}]}}},
    ),  # Filtering
    ('{ TestEcho: echo(echo: "test") }', "/echo", {"data": {"TestEcho": "test"}}),  # Aliases
    (
        '{ search(contains: "A") { __typename ... on Book { name } } }',
        "/search<Book>.name",
        {
            "data": {
                "search": [
                    {"__typename": "Book", "name": "Python Agent: The Book"},
                    {"__typename": "Book", "name": "Ollies for O11y: A Sk8er's Guide to Observability"},
                ]
            }
        },
    ),  # InlineFragment
    (
        '{ hello echo(echo: "test") }',
        "",
        {"data": {"hello": "Hello!", "echo": "test"}},
    ),  # Multiple root selections. (need to decide on final behavior)
    # FragmentSpread
    (
        "{ library(index: 0) { book { ...MyFragment } } } fragment MyFragment on Book { name }",  # Fragment filtering
        "/library.book.name",
        {"data": {"library": {"book": [{"name": "Python Agent: The Book"}, {"name": "[Redacted]"}]}}},
    ),
    (
        "{ library(index: 0) { book { ...MyFragment } } } fragment MyFragment on Book { author { first_name } }",
        "/library.book.author.first_name",
        {"data": {"library": {"book": [{"author": {"first_name": "New"}}, {"author": {"first_name": "Leslie"}}]}}},
    ),
    (
        "{ library(index: 0) { book { ...MyFragment } magazine { ...MagFragment } } } fragment MyFragment on Book { author { first_name } } fragment MagFragment on Magazine { name }",
        "/library",
        {
            "data": {
                "library": {
                    "book": [{"author": {"first_name": "New"}}, {"author": {"first_name": "Leslie"}}],
                    "magazine": [{"name": "Reli Updates Weekly"}, {"name": "Node Weekly"}],
                }
            }
        },
    ),
]


@pytest.mark.parametrize("query,expected_path,result", _test_queries)
def test_query(wsgi_app, query, expected_path, result):
    transaction_name = f"query/<anonymous>{expected_path}"

    @validate_transaction_metrics(transaction_name, "GraphQL", rollup_metrics=_graphql_base_rollup_metrics)
    def _test():
        request_body = {"query": query}
        response = wsgi_app.post_json("/graphql", request_body)
        assert response.json == result

    _test()


@dt_enabled
def test_operation_metrics_and_attrs(wsgi_app):
    operation_metrics = [("GraphQL/operation/GrapheneDjango/query/MyQuery/library", 1)]

    @validate_span_events(
        exact_agents={
            "graphql.operation.type": "query",
            "graphql.operation.name": "MyQuery",
            "graphql.operation.query": "query MyQuery { library(index: ?) { branch, book { name } } }",
        }
    )
    @validate_span_events(
        exact_agents={
            "response.status": "200",
            "response.headers.contentLength": 108,
            "response.headers.contentType": "application/json",
        }
    )
    @validate_transaction_metrics(
        "query/MyQuery/library",
        "GraphQL",
        scoped_metrics=operation_metrics,
        rollup_metrics=operation_metrics + _graphql_base_rollup_metrics,
    )
    def _test():
        request_body = {"query": "query MyQuery { library(index: 0) { branch, book { name } } }"}
        response = wsgi_app.post_json("/graphql", request_body)
        assert response.json

    _test()


@dt_enabled
def test_field_resolver_metrics_and_attrs(wsgi_app):
    field_resolver_metrics = [
        ("Function/_target_schema_sync:resolve_library", 1),
        ("GraphQL/resolve/GrapheneDjango/library", 1),
        ("GraphQL/resolve/GrapheneDjango/branch", 1),
        ("GraphQL/resolve/GrapheneDjango/book", 1),
    ]

    @validate_span_events(
        exact_agents={
            "graphql.field.name": "library",
            "graphql.field.parentType": "Query",
            "graphql.field.path": "library",
            "graphql.field.returnType": "Library",
        }
    )
    @validate_span_events(
        exact_agents={
            "response.status": "200",
            "response.headers.contentLength": 108,
            "response.headers.contentType": "application/json",
        }
    )
    @validate_transaction_metrics(
        "query/MyQuery/library",
        "GraphQL",
        scoped_metrics=field_resolver_metrics,
        rollup_metrics=field_resolver_metrics + _graphql_base_rollup_metrics,
    )
    def _test():
        request_body = {"query": "query MyQuery { library(index: 0) { branch, book { name } } }"}
        response = wsgi_app.post_json("/graphql", request_body)
        assert response.json

    _test()


def test_mutate(wsgi_app):
    _test_mutation_scoped_metrics = [
        ("GraphQL/resolve/GrapheneDjango/storage_add", 1),
        ("GraphQL/operation/GrapheneDjango/mutation/<anonymous>/storage_add.string", 1),
    ]

    @validate_transaction_metrics(
        "mutation/<anonymous>/storage_add.string",
        "GraphQL",
        scoped_metrics=_test_mutation_scoped_metrics,
        rollup_metrics=_test_mutation_scoped_metrics + _graphql_base_rollup_metrics,
    )
    def _test():
        query = 'mutation { storage_add(string: "abc") { string } }'
        request_body = {"query": query}
        response = wsgi_app.post_json("/graphql", request_body)
        assert response.json == {"data": {"storage_add": {"string": "abc"}}}

    _test()
