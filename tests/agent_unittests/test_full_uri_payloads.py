import os
import pytest
import time

from newrelic.core.config import global_settings, global_settings_dump
from newrelic.core.data_collector import (create_session, collector_url,
        send_request, ApplicationSession)
from newrelic.packages.requests.adapters import HTTPAdapter, urldefragauth
from newrelic.packages.requests import Session


class FullURIAdapter(HTTPAdapter):
    def request_url(self, request, proxies):
        return urldefragauth(request.url)


class FullURIApplicationSession(ApplicationSession):

    @classmethod
    def send_request(cls, session, url, method, license_key,
            agent_run_id=None, payload=()):
        session = Session()

        # Mount an adapter that will force the full URI to be sent
        session.mount('https://', FullURIAdapter())
        session.mount('http://', FullURIAdapter())

        return ApplicationSession.send_request(
                session, url, method, license_key, agent_run_id, payload
        )


@pytest.fixture(scope='module')
def base_settings():
    settings = global_settings()

    settings.license_key = os.environ.get('NEW_RELIC_LICENSE_KEY',
            '84325f47e9dec80613e262be4236088a9983d501')
    settings.host = os.environ.get('NEW_RELIC_HOST',
            'staging-collector.newrelic.com')
    settings.port = int(os.environ.get('NEW_RELIC_PORT', '0'))

    return settings


@pytest.fixture(scope='module')
def session(base_settings):
    environment = ()
    linked_apps = []
    app_name = 'Python Agent Test'

    session = create_session(
            None, app_name, linked_apps, environment, global_settings_dump())

    # Mount an adapter that will force the full URI to be sent
    assert session._requests_session is session.requests_session
    original_adapters = session.requests_session.adapters.copy()

    session.requests_session.mount('https://', FullURIAdapter())
    session.requests_session.mount('http://', FullURIAdapter())

    yield session

    # Restore the original HTTP adapters
    session.requests_session.adapters = original_adapters

    session.shutdown_session()


NOW = time.time()
EMPTY_SAMPLES = {
    'reservoir_size': 100,
    'events_seen': 0,
}


@pytest.mark.parametrize('method,args', [
    ('send_metric_data', (NOW, NOW + 1, ())),
    ('send_transaction_events', ((),)),
    ('send_custom_events', (EMPTY_SAMPLES, ())),
    ('send_error_events', (EMPTY_SAMPLES, ())),
    ('send_transaction_traces', ([[]],)),
    ('send_sql_traces', ([[]],)),
    ('get_agent_commands', ()),
    ('send_profile_data', ([[]],)),
    ('get_xray_metadata', (0,)),
    ('send_errors', ([[]],)),
    ('send_agent_command_results', ({0: {}},)),
])
def test_full_uri_payload(session, method, args):
    sender = getattr(session, method)

    # An exception will be raised here if there's a problem with the response
    sender(*args)


def test_full_uri_preconnect(base_settings):
    session = Session()

    # Mount an adapter that will force the full URI to be sent
    session.mount('https://', FullURIAdapter())
    session.mount('http://', FullURIAdapter())

    # An exception will be raised here if there's a problem with the response
    send_request(session, collector_url(), 'preconnect',
            base_settings.license_key)


def test_full_uri_protocol_15(base_settings):
    environment = ()
    linked_apps = []
    app_name = 'Python Agent Test'

    session = FullURIApplicationSession.create_session(
            None, app_name, linked_apps, environment, global_settings_dump())
    session.shutdown_session()
