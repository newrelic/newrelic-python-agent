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

import http.client

import pytest
from testing_support.external_fixtures import cache_outgoing_headers
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_distributed_tracing_headers import validate_distributed_tracing_headers
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def metrics(server):
    _external_metric = f"External/localhost:{server.port}/http/"

    scoped = [(_external_metric, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        (f"External/localhost:{server.port}/all", 1),
        (_external_metric, 1),
    ]

    return scoped, rollup


def test_http_http_request(server, metrics):
    @validate_transaction_metrics(
        "test_http:test_http_http_request", scoped_metrics=metrics[0], rollup_metrics=metrics[1], background_task=True
    )
    @background_task(name="test_http:test_http_http_request")
    def _test():
        connection = http.client.HTTPConnection("localhost", server.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read()
        connection.close()

    _test()


def test_http_https_request(server, metrics):
    @validate_transaction_metrics(
        "test_http:test_http_https_request", scoped_metrics=metrics[0], rollup_metrics=metrics[1], background_task=True
    )
    @background_task(name="test_http:test_http_https_request")
    def _test():
        connection = http.client.HTTPSConnection("localhost", server.port)
        try:
            connection.request("GET", "/")
        except Exception:
            pass
        connection.close()

    _test()


@pytest.mark.parametrize("distributed_tracing,span_events", ((True, True), (True, False), (False, False)))
def test_http_distributed_tracing_request(distributed_tracing, span_events, server):
    @background_task(name="test_http:test_http_distributed_tracing_request")
    @cache_outgoing_headers
    @validate_distributed_tracing_headers
    def _test():
        connection = http.client.HTTPConnection("localhost", server.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read()
        connection.close()

    _test = override_application_settings(
        {"distributed_tracing.enabled": distributed_tracing, "span_events.enabled": span_events}
    )(_test)

    _test()
