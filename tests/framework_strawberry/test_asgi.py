import json

import pytest
from testing_support.asgi_testing import AsgiTest
from testing_support.fixtures import dt_enabled, validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events


@pytest.fixture(scope="session")
def graphql_asgi_run():
    """Wrapper function to simulate framework_graphql test behavior."""
    from _target_application import _target_asgi_application

    app = AsgiTest(_target_asgi_application)

    def execute(query):
        return app.make_request(
            "POST",
            "/",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"query": query}),
        )

    return execute


@dt_enabled
def test_query_and_mutation_asgi(graphql_asgi_run):
    from graphql import __version__ as version

    from newrelic.hooks.framework_strawberry import framework_details

    FRAMEWORK_METRICS = [
        ("Python/Framework/Strawberry/%s" % framework_details()[1], 1),
        ("Python/Framework/GraphQL/%s" % version, 1),
    ]
    _test_mutation_scoped_metrics = [
        ("GraphQL/resolve/Strawberry/storage_add", 1),
        ("GraphQL/operation/Strawberry/mutation/<anonymous>/storage_add", 1),
    ]
    _test_query_scoped_metrics = [
        ("GraphQL/resolve/Strawberry/storage", 1),
        ("GraphQL/operation/Strawberry/query/<anonymous>/storage", 1),
    ]
    _test_unscoped_metrics = [
        ("WebTransaction", 1),
        ("GraphQL/all", 1),
        ("GraphQL/Strawberry/all", 1),
        ("GraphQL/allWeb", 1),
        ("GraphQL/Strawberry/allWeb", 1),
    ]
    _test_mutation_unscoped_metrics = _test_unscoped_metrics + _test_mutation_scoped_metrics
    _test_query_unscoped_metrics = _test_unscoped_metrics + _test_query_scoped_metrics

    _expected_mutation_operation_attributes = {
        "graphql.operation.type": "mutation",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_mutation_resolver_attributes = {
        "graphql.field.name": "storage_add",
        "graphql.field.parentType": "Mutation",
        "graphql.field.path": "storage_add",
        "graphql.field.returnType": "String!",
    }
    _expected_query_operation_attributes = {
        "graphql.operation.type": "query",
        "graphql.operation.name": "<anonymous>",
    }
    _expected_query_resolver_attributes = {
        "graphql.field.name": "storage",
        "graphql.field.parentType": "Query",
        "graphql.field.path": "storage",
        "graphql.field.returnType": "[String!]!",
    }

    @validate_transaction_metrics(
        "query/<anonymous>/storage",
        "GraphQL",
        scoped_metrics=_test_query_scoped_metrics,
        rollup_metrics=_test_query_unscoped_metrics + FRAMEWORK_METRICS,
    )
    @validate_transaction_metrics(
        "mutation/<anonymous>/storage_add",
        "GraphQL",
        scoped_metrics=_test_mutation_scoped_metrics,
        rollup_metrics=_test_mutation_unscoped_metrics + FRAMEWORK_METRICS,
        index=-2,
    )
    @validate_span_events(exact_agents=_expected_mutation_operation_attributes, index=-2)
    @validate_span_events(exact_agents=_expected_mutation_resolver_attributes, index=-2)
    @validate_span_events(exact_agents=_expected_query_operation_attributes)
    @validate_span_events(exact_agents=_expected_query_resolver_attributes)
    def _test():
        response = graphql_asgi_run('mutation { storage_add(string: "abc") }')
        assert response.status == 200
        response = json.loads(response.body.decode("utf-8"))
        assert not response.get("errors")

        response = graphql_asgi_run("query { storage }")
        assert response.status == 200
        response = json.loads(response.body.decode("utf-8"))
        assert not response.get("errors")

        # These are separate assertions because pypy stores 'abc' as a unicode string while other Python versions do not
        assert "storage" in str(response.get("data"))
        assert "abc" in str(response.get("data"))

    _test()
