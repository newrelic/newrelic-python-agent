import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)

_coverage_source = [
    'newrelic.api.external_trace',
    'newrelic.hooks.external_urllib3',
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
        app_name='Python Agent Test (external_urllib3)',
        default_settings=_default_settings)

@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass

@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass

@pytest.fixture(scope='session')
def server():
    with MockExternalHTTPHResponseHeadersServer() as _server:
        yield _server
