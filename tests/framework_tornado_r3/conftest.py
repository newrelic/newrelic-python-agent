import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture, collector_available_fixture,
        initialize_agent)

from tornado_fixtures import (wrap_record_transaction_fixture,
        clear_record_transaction_list, wrap_record_app_exception_fixture,
        clear_record_app_exception_list)

_default_settings = {
    'feature_flag': set(['tornado.instrumentation.r3']),
    'transaction_tracer.explain_threshold': 0.0,
    'transaction_tracer.transaction_threshold': 0.0,
    'transaction_tracer.stack_trace_threshold': 0.0,
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
}

# We want to initialize the new relic agent before any tornado modules get
# imported. This is because we wrap tornado decorators which are run at
# import time. If we wait to wrap tornado modules when the pytest session
# starts, it will be to late too wrap these decorators.
# Initializing the agent before the coverage module is run will cause it
# to log a warning since it is concerned about missing coverage before it was
# loaded. This is not an issue for us since, while we import the instrumentation
# first, we don't run any tests until after the coverage module is loaded.
initialize_agent(app_name='Python Agent Test (framework_tornado_r3)',
        default_settings=_default_settings)

collector_agent_registration = collector_agent_registration_fixture(
        app_name='Python Agent Test (framework_tornado_r3)',
        default_settings=_default_settings, should_initialize_agent=False)

_coverage_source = [
    'newrelic.hooks.framework_tornado_r3',
]

code_coverage = code_coverage_fixture(source=_coverage_source)

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
