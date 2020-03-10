import pytest

from testing_support.fixtures import (code_coverage_fixture,
        collector_agent_registration_fixture)

_coverage_source = [
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
        app_name='Python Agent Test (backend_mtb)',
        default_settings=_default_settings)


@pytest.fixture(scope='session')
def session_initialization(code_coverage, collector_agent_registration):
    pass


@pytest.fixture(scope='function')
def requires_data_collector(collector_available_fixture):
    pass


@pytest.fixture(scope='module')
def grpc_add_to_server():
    from newrelic.core.mtb_pb2_grpc import add_IngestServiceServicer_to_server

    return add_IngestServiceServicer_to_server


@pytest.fixture(scope='module')
def grpc_servicer():
    from _test_servicer import Servicer

    return Servicer()


@pytest.fixture(scope='module')
def grpc_stub_cls(grpc_channel):
    from newrelic.core.mtb_pb2_grpc import IngestServiceStub

    return IngestServiceStub
