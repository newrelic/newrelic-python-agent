import pytest

from testing_support.fixtures import (
        collector_available_fixture,
        code_coverage_fixture,
        collector_agent_registration_fixture)

_coverage_source = [
    'newrelic.hooks.coroutines_asyncio',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (coroutines_asyncio)',
        default_settings=_default_settings)


@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass
