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
import six
from testing_support.external_fixtures import (
    cache_outgoing_headers,
    insert_incoming_headers,
)
from testing_support.fixtures import (
    cat_enabled,
    override_application_settings,
)
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers,
)
from testing_support.validators.validate_external_node_params import (
    validate_external_node_params,
)

from newrelic.api.background_task import background_task

if six.PY2:
    import httplib
else:
    import http.client as httplib


@pytest.fixture(scope="session")
def metrics(server):
    if six.PY2:
        _external_metric = "External/localhost:%s/httplib/" % server.port
    else:
        _external_metric = "External/localhost:%s/http/" % server.port

    scoped = [(_external_metric, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%s/all" % server.port, 1),
        (_external_metric, 1),
    ]

    return scoped, rollup


def test_http_http_request(server, metrics):
    @validate_transaction_metrics(
        "test_http:test_http_http_request", scoped_metrics=metrics[0], rollup_metrics=metrics[1], background_task=True
    )
    @background_task(name="test_http:test_http_http_request")
    def _test():
        connection = httplib.HTTPConnection("localhost", server.port)
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
        connection = httplib.HTTPSConnection("localhost", server.port)
        try:
            connection.request("GET", "/")
        except Exception:
            pass
        connection.close()

    _test()


@pytest.mark.parametrize(
    "distributed_tracing,span_events",
    (
        (True, True),
        (True, False),
        (False, False),
    ),
)
def test_http_cross_process_request(distributed_tracing, span_events, server):
    @background_task(name="test_http:test_http_cross_process_request")
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        connection = httplib.HTTPConnection("localhost", server.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read()
        connection.close()

    _test = override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "cross_application_tracer.enabled": not distributed_tracing,
            "span_events.enabled": span_events,
        }
    )(_test)

    _test()


@cat_enabled
def test_http_cross_process_response(server):
    _test_http_cross_process_response_scoped_metrics = [("ExternalTransaction/localhost:%s/1#2/test" % server.port, 1)]

    _test_http_cross_process_response_rollup_metrics = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%s/all" % server.port, 1),
        ("ExternalApp/localhost:%s/1#2/all" % server.port, 1),
        ("ExternalTransaction/localhost:%s/1#2/test" % server.port, 1),
    ]

    _test_http_cross_process_response_external_node_params = [
        ("cross_process_id", "1#2"),
        ("external_txn_name", "test"),
        ("transaction_guid", "0123456789012345"),
    ]

    @validate_transaction_metrics(
        "test_http:test_http_cross_process_response",
        scoped_metrics=_test_http_cross_process_response_scoped_metrics,
        rollup_metrics=_test_http_cross_process_response_rollup_metrics,
        background_task=True,
    )
    @insert_incoming_headers
    @validate_external_node_params(params=_test_http_cross_process_response_external_node_params)
    @background_task(name="test_http:test_http_cross_process_response")
    def _test():
        connection = httplib.HTTPConnection("localhost", server.port)
        connection.request("GET", "/")
        response = connection.getresponse()
        response.read()
        connection.close()

    _test()
