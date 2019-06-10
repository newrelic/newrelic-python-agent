import newrelic.packages.six as six
import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

_coverage_source = [
    'newrelic.api.transaction',
    'newrelic.api.web_transaction',
    'newrelic.common.coroutine',
    'newrelic.api.lambda_handler'
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
    'debug.log_autorum_middleware': True,
    'agent_limits.errors_per_harvest': 100,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (agent_features)',
        default_settings=_default_settings)


@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass


@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass


if six.PY2:
    collect_ignore = ['test_coroutine_transaction.py', 'test_async_timing.py',
            'test_asyncio_transactions.py']
