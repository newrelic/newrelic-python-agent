import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture)

from tornado_fixtures import (wrap_record_transaction_fixture,
        clear_record_transaction_list, wrap_record_app_exception_fixture,
        clear_record_app_exception_list)

_coverage_source = [
    'newrelic.hooks.framework_tornado_r3',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    'feature_flag': set(['tornado.instrumentation.r3']),
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (framework_tornado_r3)',
        default_settings=_default_settings)

@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration,
        wrap_record_transaction_fixture, wrap_record_app_exception_fixture):
    pass

@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass

@pytest.fixture(scope='function')
def prepare_record_transaction(clear_record_transaction_list):
    pass

@pytest.fixture(scope='function')
def prepare_record_app_exception(clear_record_app_exception_list):
    pass
