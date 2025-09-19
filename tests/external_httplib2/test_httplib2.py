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

import httplib2
import pytest
from testing_support.external_fixtures import cache_outgoing_headers
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_cross_process_headers import validate_cross_process_headers
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def metrics(server):
    scoped = [(f"External/localhost:{server.port}/httplib2/", 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        (f"External/localhost:{server.port}/all", 1),
        (f"External/localhost:{server.port}/httplib2/", 1),
    ]

    return scoped, rollup


def test_httplib2_http_connection_request(server, metrics):
    @validate_transaction_metrics(
        "test_httplib2:test_httplib2_http_connection_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_httplib2:test_httplib2_http_connection_request")
    def _test():
        connection = httplib2.HTTPConnectionWithTimeout("localhost", server.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read()
        connection.close()

    _test()


def test_httplib2_https_connection_request(server, metrics):
    @validate_transaction_metrics(
        "test_httplib2:test_httplib2_https_connection_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_httplib2:test_httplib2_https_connection_request")
    def _test():
        connection = httplib2.HTTPSConnectionWithTimeout("localhost", server.port)
        try:
            connection.request("GET", "/")
        except Exception:
            pass
        connection.close()

    _test()


def test_httplib2_http_request(server, metrics):
    @validate_transaction_metrics(
        "test_httplib2:test_httplib2_http_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_httplib2:test_httplib2_http_request")
    def _test():
        connection = httplib2.Http()
        response, content = connection.request(f"http://localhost:{server.port}", "GET")

    _test()


@pytest.mark.parametrize("distributed_tracing,span_events", ((True, True), (True, False), (False, False)))
def test_httplib2_cross_process_request(distributed_tracing, span_events, server):
    @background_task(name="test_httplib2:test_httplib2_cross_process_response")
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        connection = httplib2.HTTPConnectionWithTimeout("localhost", server.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read()
        connection.close()

    _test = override_application_settings(
        {"distributed_tracing.enabled": distributed_tracing, "span_events.enabled": span_events}
    )(_test)

    _test()
