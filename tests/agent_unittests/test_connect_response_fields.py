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
