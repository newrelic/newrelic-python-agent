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
import requests

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)
from testing_support.mock_external_http_server import MockExternalHTTPServer
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction


@pytest.fixture(scope='module', autouse=True)
def server():
    with MockExternalHTTPServer() as _server:
        yield _server


@pytest.mark.parametrize('path', ('', '/foo', '/' + 'a' * 256))
def test_span_events(server, path):
    _settings = {
        'distributed_tracing.enabled': True,
        'span_events.enabled': True,
    }

    uri = 'http://localhost:%d' % server.port
    if path:
        uri += path

    # Validate long uri gets truncated
    expected_uri = uri[:255]

    exact_intrinsics = {
        'name': 'External/localhost:%d/requests/' % server.port,
        'type': 'Span',
        'sampled': True,
        'priority': 0.5,

        'category': 'http',
        'span.kind': 'client',
        'component': 'requests',
    }
    exact_agents = {
        'http.url': expected_uri,
    }
    expected_intrinsics = ('timestamp', 'duration', 'transactionId')

    @override_application_settings(_settings)
    @validate_span_events(
            count=1,
            exact_intrinsics=exact_intrinsics,
            exact_agents=exact_agents,
            expected_intrinsics=expected_intrinsics)
    @background_task(name='test_span_events')
    def _test():
        txn = current_transaction()
        txn._priority = 0.5
        txn._sampled = True

        response = requests.get(uri)
        response.raise_for_status()

    _test()
