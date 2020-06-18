# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import time

from testing_support.fixtures import (override_generic_settings,
        collector_agent_registration_fixture, initialize_agent)
from newrelic.core.config import global_settings, global_settings_dump
from newrelic.core.data_collector import ApplicationSession
from newrelic.packages.requests.adapters import HTTPAdapter, urldefragauth
from newrelic.packages.requests import Session


class FullURIAdapter(HTTPAdapter):
    def request_url(self, request, proxies):
        return urldefragauth(request.url)


class FullURIApplicationSession(ApplicationSession):

    @classmethod
    def send_request(cls, session, *args, **kwargs):
        session = Session()

        # Mount an adapter that will force the full URI to be sent
        session.mount('https://', FullURIAdapter())
        session.mount('http://', FullURIAdapter())

        return ApplicationSession.send_request(
                session, *args, **kwargs
        )


_default_settings = {
    'debug.log_data_collector_payloads': True,
    'debug.record_transaction_failure': True,
    'startup_timeout': 10.0,
}
application = collector_agent_registration_fixture(
        app_name='Python Agent Test (test_full_uri_payloads)',
        default_settings=_default_settings)


@pytest.fixture(scope='module')
def session(application):
    session = application._agent.application(application.name)._active_session
    assert session is not None

    # Mount an adapter that will force the full URI to be sent
    for _ in range(3):
        # connect_to_data_collector will close the session once a connection
        # has been established. Force a context switch and wait for this to
        # happen.
        time.sleep(0.1)
        if session._requests_session is None:
            break
    else:
        assert False, "Session was never closed during connect."

    # Force a new request session to be created and store the id
    before_id = id(session.requests_session)

    original_adapters = session.requests_session.adapters.copy()

    session.requests_session.mount('https://', FullURIAdapter())
    session.requests_session.mount('http://', FullURIAdapter())

    yield session

    # Check that the requests session hasn't been modified
    assert before_id == id(session.requests_session)

    # Restore the original HTTP adapters
    session.requests_session.adapters = original_adapters


NOW = time.time()
EMPTY_SAMPLES = {
    'reservoir_size': 100,
    'events_seen': 0,
}


_override_settings = {'agent_limits.data_compression_threshold': 0}


@pytest.mark.parametrize('method,args', [
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
])
@override_generic_settings(global_settings(), _override_settings)
def test_full_uri_payload(session, method, args):
    sender = getattr(session, method)

    # An exception will be raised here if there's a problem with the response
    sender(*args)


_override_settings = {'compressed_content_encoding': 'deflate',
            'agent_limits.data_compression_threshold': 0}


@pytest.mark.parametrize('method,args', [
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
])
@override_generic_settings(global_settings(), _override_settings)
def test_compression_deflate(session, method, args):
    sender = getattr(session, method)

    # An exception will be raised here if there's a problem with the response
    sender(*args)


def test_full_uri_protocol_lifecycle():
    """Exercises the following endpoints:

    * preconnect
    * connect
    * shutdown
    """
    initialize_agent(
        app_name='Python Agent Test (test_full_uri_payloads)',
        default_settings=_default_settings)

    environment = ()
    linked_apps = []

    session = FullURIApplicationSession.create_session(
            None, global_settings().app_name,
            linked_apps, environment, global_settings_dump())
    session.shutdown_session()
