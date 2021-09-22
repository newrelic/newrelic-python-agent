import pytest
import webtest
from testing_support.fixtures import dt_enabled, validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events


@pytest.fixture(scope="session")
def graphql_wsgi_run():
    """Wrapper function to simulate framework_graphql test behavior."""
    from _target_application import _target_wsgi_application

    app = webtest.TestApp(_target_wsgi_application)

    def execute(query):
        return app.post_json("/", {"query": query})

    return execute


@dt_enabled
def test_query_and_mutation_wsgi(graphql_wsgi_run):
    from graphql import __version__ as version

    FRAMEWORK_METRICS = [
        ("Python/Framework/Ariadne/None", 1),
        ("Python/Framework/GraphQL/%s" % version, 1),
    ]
    _test_mutation_scoped_metrics = [
        ("GraphQL/resolve/Ariadne/storage_add", 1),
        ("GraphQL/operation/Ariadne/mutation/<anonymous>/storage_add.string", 1),
    ]
    _test_query_scoped_metrics = [
        ("GraphQL/resolve/Ariadne/storage", 1),
        ("GraphQL/operation/Ariadne/query/<anonymous>/storage", 1),
    ]
    _test_unscoped_metrics = [
        ("WebTransaction", 1),
        ("Python/WSGI/Response", 1),
        ("GraphQL/all", 1),
        ("GraphQL/Ariadne/all", 1),
        ("GraphQL/allWeb", 1),
        ("GraphQL/Ariadne/allWeb", 1),
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
        scoped_metrics=_test_query_scoped_metrics,
        rollup_metrics=_test_query_unscoped_metrics + FRAMEWORK_METRICS,
    )
    @validate_transaction_metrics(
        "mutation/<anonymous>/storage_add.string",
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
        response = graphql_wsgi_run('mutation { storage_add(string: "abc") { string } }')
        assert response.status_code == 200
        response = response.json_body
        assert not response.get("errors")

        response = graphql_wsgi_run("query { storage }")
        assert response.status_code == 200
        response = response.json_body
        assert not response.get("errors")

        # These are separate assertions because pypy stores 'abc' as a unicode string while other Python versions do not
        assert "storage" in str(response.get("data"))
        assert "abc" in str(response.get("data"))

    _test()
