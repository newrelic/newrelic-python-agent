import pytest
import webtest
from testing_support.fixtures import (code_coverage_fixture,  # noqa
        collector_agent_registration_fixture, collector_available_fixture)

_default_settings = {
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (component_piston)',
        default_settings=_default_settings)

_coverage_source = [
    'newrelic.hooks.component_piston',
]

code_coverage = code_coverage_fixture(source=_coverage_source)


@pytest.fixture(scope='session')
def app():
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from _target_application import wsgi
    return webtest.TestApp(wsgi())
