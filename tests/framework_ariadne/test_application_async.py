import asyncio

import pytest
from testing_support.fixtures import dt_enabled, validate_transaction_metrics
from testing_support.validators.validate_span_events import validate_span_events

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def graphql_run_async():
    """Wrapper function to simulate framework_graphql test behavior."""

    def execute(schema, query, *args, **kwargs):
        from ariadne import graphql

        return graphql(schema, {"query": query}, *args, **kwargs)

    return execute


@dt_enabled
def test_query_and_mutation_async(app, graphql_run_async):
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
        async def coro():
            ok, response = await graphql_run_async(app, 'mutation { storage_add(string: "abc") { string } }')
            assert ok and not response.get("errors")
            ok, response = await graphql_run_async(app, "query { storage }")
            assert ok and not response.get("errors")

            # These are separate assertions because pypy stores 'abc' as a unicode string while other Python versions do not
            assert "storage" in str(response.get("data"))
            assert "abc" in str(response.get("data"))

        loop = asyncio.new_event_loop()
        loop.run_until_complete(coro())

    _test()
