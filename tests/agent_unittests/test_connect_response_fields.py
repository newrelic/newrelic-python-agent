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
import functools
import time

from testing_support.fixtures import override_generic_settings
from newrelic.core.config import global_settings
from newrelic.core.agent_protocol import AgentProtocol
from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.encoding_utils import json_encode


DEFAULT = object()
LINKED_APPLICATIONS = []
ENVIRONMENT = []
NOW = time.time()
EMPTY_SAMPLES = {
    'reservoir_size': 100,
    'events_seen': 0,
}


_all_endpoints = (
    ('send_metric_data', (NOW, NOW + 1, ())),
    ('send_transaction_events', (EMPTY_SAMPLES, ())),
    ('send_custom_events', (EMPTY_SAMPLES, ())),
    ('send_error_events', (EMPTY_SAMPLES, ())),
    ('send_transaction_traces', ([[]],)),
    ('send_sql_traces', ([[]],)),
    ('get_agent_commands', ()),
    ('send_profile_data', ([[]],)),
    ('send_errors', ([[]],)),
    ('send_agent_command_results', ({0: {}},)),
    ('agent_settings', ({},)),
    ('send_span_events', (EMPTY_SAMPLES, ())),
    ('shutdown_session', ()),
)


class CustomTestClient(DeveloperModeClient):
    def __init__(self, connect_response_fields, *args, **kwargs):
        super(CustomTestClient, self).__init__(*args, **kwargs)
        self.connect_response_fields = connect_response_fields
        self.headers = []

    def log_request(self, fp, method, url, params, payload, headers):
        self.headers.append(headers)
        return super(CustomTestClient, self).log_request(fp, method, url, params, payload, headers)

    def send_request(
        self,
        method="POST",
        path="/agent_listener/invoke_raw_method",
        params=None,
        headers=None,
        payload=None,
    ):
        agent_method = params["method"]
        if agent_method == "connect" and self.connect_response_fields is not DEFAULT:
            connect_response = dict(self.RESPONSES[agent_method])
            connect_response.update(self.connect_response_fields)
            payload = {"return_value": connect_response}
            response_data = json_encode(payload).encode("utf-8")
            return (200, response_data)
        else:
            return super(CustomTestClient, self).send_request(
                method,
                path,
                params,
                headers,
                payload,
            )


@pytest.mark.parametrize('headers_map_present', (True, False))
def test_no_blob_behavior(headers_map_present):
    if headers_map_present:
        connect_response_fields = {u"request_headers_map": None}
        client_cls = functools.partial(
                CustomTestClient, connect_response_fields=connect_response_fields)
    else:
        client_cls = functools.partial(
                CustomTestClient, connect_response_fields=DEFAULT)

    protocol = AgentProtocol.connect(
            'app_name',
            LINKED_APPLICATIONS,
            ENVIRONMENT,
            global_settings(),
            client_cls=client_cls)

    protocol.send("shutdown")

    headers = protocol.client.headers[-1]
    assert headers == {
        "Content-Type": "application/json",
    }


def test_blob():
    request_headers_map = {u'X-Foo': u'Bar'}
    connect_response_fields = {u"request_headers_map": request_headers_map}

    client_cls = functools.partial(
            CustomTestClient,
            connect_response_fields=connect_response_fields)

    protocol = AgentProtocol.connect(
            'app_name',
            LINKED_APPLICATIONS,
            ENVIRONMENT,
            global_settings(),
            client_cls=client_cls)

    protocol.send("shutdown")

    headers = protocol.client.headers[-1]
    assert headers == {
        "Content-Type": "application/json",
        "X-Foo": "Bar",
    }


@override_generic_settings(global_settings(), {
    'developer_mode': True,
})
def test_server_side_config_precedence():
    connect_response_fields = {
        u'agent_config': {u'span_events.enabled': True},
        u'span_events.enabled': False,
    }
    client_cls = functools.partial(
            CustomTestClient,
            connect_response_fields=connect_response_fields)

    protocol = AgentProtocol.connect(
            'app_name',
            LINKED_APPLICATIONS,
            ENVIRONMENT,
            global_settings(),
            client_cls=client_cls)

    assert protocol.configuration.span_events.enabled is False
