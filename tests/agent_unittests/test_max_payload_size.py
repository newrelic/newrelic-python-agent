import pytest
import time
from newrelic.core.config import global_settings, global_settings_dump
from newrelic.core.data_collector import create_session
from testing_support.fixtures import initialize_agent
from newrelic.network.exceptions import DiscardDataForRequest


_default_settings = {
    'agent_limits.data_compression_threshold': 10000000,
    'debug.record_transaction_failure': True,
    'startup_timeout': 10.0,
}
NOW = time.time()
EMPTY_SAMPLES = {
    'reservoir_size': 100,
    'events_seen': 0,
}
GARBAGE = ['garbage'] * 1024


@pytest.fixture(scope='module')
def session():
    initialize_agent(
        app_name='Python Agent Test (test_max_payload_size)',
        default_settings=_default_settings)

    session = create_session(
            None, global_settings().app_name, [], (), global_settings_dump())

    # Disable outbound requests
    assert session._requests_session is session.requests_session
    original_request = session.requests_session.request

    def request(*args, **kwargs):
        assert False, "Outbound request made"

    # Disable all requests
    session.requests_session.request = request

    yield session

    # Re-enable requests
    session.requests_session.request = original_request
    session.shutdown_session()


@pytest.mark.parametrize('method,args', [
    ('send_metric_data', (NOW, NOW + 1, GARBAGE)),
    ('send_transaction_events', (GARBAGE,)),
    ('send_custom_events', (EMPTY_SAMPLES, GARBAGE)),
    ('send_error_events', (EMPTY_SAMPLES, GARBAGE)),
    ('send_transaction_traces', (GARBAGE,)),
    ('send_sql_traces', (GARBAGE,)),
    ('send_profile_data', (GARBAGE,)),
    ('get_xray_metadata', (GARBAGE, )),
    ('send_errors', (GARBAGE,)),
    ('send_agent_command_results', (GARBAGE,)),
    ('agent_settings', (GARBAGE,)),
    ('send_span_events', (EMPTY_SAMPLES, GARBAGE)),
])
def test_max_payload_size(session, method, args):
    sender = getattr(session, method)
    session.configuration.max_payload_size_in_bytes = 1024

    with pytest.raises(DiscardDataForRequest):
        sender(*args)
