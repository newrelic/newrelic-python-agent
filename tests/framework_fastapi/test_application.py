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
from testing_support.fixtures import dt_enabled, validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events


@pytest.mark.parametrize("endpoint,transaction_name", (
    ("/sync", "_target_application:sync"),
    ("/async", "_target_application:non_sync"),
))
def test_application(app, endpoint, transaction_name):
    @validate_transaction_metrics(transaction_name,
        scoped_metrics=[("Function/" + transaction_name, 1)])
    def _test():
        response = app.get(endpoint)
        assert response.status == 200

    _test()


@dt_enabled
def test_graphql_endpoint(app):
    from graphql import __version__ as version

    FRAMEWORK_METRICS = [
        ("Python/Framework/GraphQL/%s" % version, 1),
    ]
    _test_scoped_metrics = [
        ("GraphQL/resolve/GraphQL/hello", 1),
        ("GraphQL/operation/GraphQL/query/<anonymous>/hello", 1),
    ]
    _test_unscoped_metrics = [
        ("GraphQL/all", 1),
        ("GraphQL/GraphQL/all", 1),
        ("GraphQL/allWeb", 1),
        ("GraphQL/GraphQL/allWeb", 1),
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
        response = app.make_request("POST", "/graphql", params="query=%7B%20hello%20%7D")
        assert response.status == 200
        assert "Hello!" in response.body.decode("utf-8")

    _test()
