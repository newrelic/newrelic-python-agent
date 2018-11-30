import pytest
import time
from copy import deepcopy

from testing_support.fixtures import override_generic_settings
from newrelic.core.config import global_settings, global_settings_dump
import newrelic.core.data_collector as data_collector


LINKED_APPLICATIONS = []
ENVIRONMENT = []
NOW = time.time()
EMPTY_SAMPLES = {
    'reservoir_size': 100,
    'events_seen': 0,
}


@pytest.fixture(autouse=True)
def restore_developer_mode():
    responses = deepcopy(data_collector._developer_mode_responses)
    log_request = data_collector._log_request
    yield
    data_collector._developer_mode_responses = responses
    data_collector._log_request = log_request


_all_endpoints = (
    ('send_metric_data', (NOW, NOW + 1, ())),
    ('send_transaction_events', (EMPTY_SAMPLES, ())),
    ('send_custom_events', (EMPTY_SAMPLES, ())),
    ('send_error_events', (EMPTY_SAMPLES, ())),
    ('send_transaction_traces', ([[]],)),
    ('send_sql_traces', ([[]],)),
    ('get_agent_commands', ()),
    ('send_profile_data', ([[]],)),
    ('get_xray_metadata', (0,)),
    ('send_errors', ([[]],)),
    ('send_agent_command_results', ({0: {}},)),
    ('agent_settings', ({},)),
    ('send_span_events', (EMPTY_SAMPLES, ())),
    ('shutdown_session', ()),
)


@pytest.mark.parametrize('method,args', _all_endpoints)
@pytest.mark.parametrize('headers_map_present', (True, False))
@override_generic_settings(global_settings(), {
    'developer_mode': True,
})
def test_no_blob_behavior(headers_map_present, method, args):
    if headers_map_present:
        connect_response = data_collector._developer_mode_responses['connect']
        connect_response[u'request_headers_map'] = None

    session = data_collector.create_session(
            'license_key',
            'app_name',
            LINKED_APPLICATIONS,
            ENVIRONMENT,
            global_settings_dump())

    check_request_called = []

    def check_request(url, params, headers, data):
        check_request_called.append(True)

        # Check that no other headers besides the default headers are present
        assert len(headers) == 2

        assert 'User-Agent' in headers
        assert headers['Content-Encoding'] == 'identity'

    data_collector._log_request = check_request
    sender = getattr(session, method)
    sender(*args)

    assert check_request_called


@pytest.mark.parametrize('method,args', _all_endpoints)
@override_generic_settings(global_settings(), {
    'developer_mode': True,
})
def test_blob(method, args):
    connect_response = data_collector._developer_mode_responses['connect']
    connect_response[u'request_headers_map'] = {u'X-Foo': u'Bar'}

    session = data_collector.create_session(
            'license_key',
            'app_name',
            LINKED_APPLICATIONS,
            ENVIRONMENT,
            global_settings_dump())

    check_request_called = []

    def check_request(url, params, headers, data):
        check_request_called.append(True)

        # Check that headers besides the one specified in the request map are
        # present
        assert len(headers) == 3

        assert headers['X-Foo'] == 'Bar'

        assert 'User-Agent' in headers
        assert headers['Content-Encoding'] == 'identity'

    data_collector._log_request = check_request
    sender = getattr(session, method)
    sender(*args)

    assert check_request_called


@override_generic_settings(global_settings(), {
    'developer_mode': True,
})
def test_server_side_config_precedence():
    connect_response = data_collector._developer_mode_responses['connect']
    connect_response[u'agent_config'] = {u'span_events.enabled': True}
    connect_response[u'span_events.enabled'] = False

    session = data_collector.create_session(
            'license_key',
            'app_name',
            LINKED_APPLICATIONS,
            ENVIRONMENT,
            global_settings_dump())

    assert session.configuration.span_events.enabled is False
