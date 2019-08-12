import pytest
from testing_support.fixtures import (code_coverage_fixture,  # noqa
        collector_agent_registration_fixture, collector_available_fixture)
from testing_support.mock_external_http_server import MockExternalHTTPServer

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (external_feedparser)',
        default_settings=_default_settings)

_coverage_source = [
    'newrelic.hooks.external_feedparser',
]

code_coverage = code_coverage_fixture(source=_coverage_source)


def create_handler(response):
    def handler(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(response)
    return handler


@pytest.fixture(scope="session")
def server():
    with open("packages.xml", "rb") as f:
        response = f.read()

    handler = create_handler(response)
    with MockExternalHTTPServer(handler=handler) as server:
        yield server
