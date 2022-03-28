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

import json

import pytest
from testing_support.fixtures import dt_enabled, validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)


@pytest.fixture(scope="session")
def target_application():
    import _test_graphql

    return _test_graphql.target_application


@dt_enabled
def test_graphql_metrics_and_attrs(target_application):
    from graphql import __version__ as graphql_version
    from graphql_server import __version__ as graphql_server_version
    from sanic import __version__ as sanic_version

    FRAMEWORK_METRICS = [
        ("Python/Framework/GraphQL/%s" % graphql_version, 1),
        ("Python/Framework/GraphQLServer/%s" % graphql_server_version, 1),
        ("Python/Framework/Sanic/%s" % sanic_version, 1),
    ]
    _test_scoped_metrics = [
        ("GraphQL/resolve/GraphQLServer/hello", 1),
        ("GraphQL/operation/GraphQLServer/query/<anonymous>/hello", 1),
        ("Function/graphql_server.sanic.graphqlview:GraphQLView.post", 1),
    ]
    _test_unscoped_metrics = [
        ("GraphQL/all", 1),
        ("GraphQL/GraphQLServer/all", 1),
        ("GraphQL/allWeb", 1),
        ("GraphQL/GraphQLServer/allWeb", 1),
    ] + _test_scoped_metrics

    _expected_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "<anonymous>",
        "graphql.operation.query": "{ hello }",
    }
    _expected_query_resolver_attributes = {
        "graphql.field.name": "hello",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "hello",
        "graphql.field.returnType": "String",
    }

    @validate_span_events(exact_agents=_expected_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_query_resolver_attributes)
    @validate_transaction_metrics(
        "query/<anonymous>/hello",
        "GraphQL",
        scoped_metrics=_test_scoped_metrics,
        rollup_metrics=_test_unscoped_metrics + FRAMEWORK_METRICS,
    )
    def _test():
        response = target_application.make_request(
            "POST", "/graphql", body=json.dumps({"query": "{ hello }"}), headers={"Content-Type": "application/json"}
        )
        assert response.status == 200
        assert "Hello!" in response.body.decode("utf-8")

    _test()


@validate_transaction_count(0)
def test_ignored_introspection_transactions(target_application):
    response = target_application.make_request(
        "POST", "/graphql", body=json.dumps({"query": "{ __schema { types { name } } }"}), headers={"Content-Type": "application/json"}
    )
    assert response.status == 200
