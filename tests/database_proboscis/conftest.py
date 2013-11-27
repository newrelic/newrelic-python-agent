import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture)

_coverage_source = [
    'newrelic.hooks.database_psycopg2',
    'newrelic.hooks.database_dbapi2',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (database_proboscis)',
        default_settings=_default_settings)

@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass
