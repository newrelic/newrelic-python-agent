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

import http.client as httplib

import pytest
from testing_support.external_fixtures import cache_outgoing_headers
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_distributed_tracing_headers import validate_distributed_tracing_headers
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_tt_segment_params import validate_tt_segment_params

from newrelic.api.background_task import background_task
from newrelic.common.encoding_utils import W3CTraceParent
from newrelic.hooks.external_httplib import NR_HEADER_KEYS


@pytest.fixture
def connection(server):
    connection_cls = httplib.HTTPSConnection if server.scheme == "https" else httplib.HTTPConnection
    conn = connection_cls("localhost", server.port)
    yield conn
    conn.close()


@pytest.fixture(params=["putrequest", "request"])
def exercise(request, connection):
    def _exercise_putrequest(path="/", headers=None):
        connection.putrequest("GET", path)
        for key, value in (headers or {}).items():
            connection.putheader(key, value)
        connection.endheaders()
        response = connection.getresponse()
        body = response.read()
        return response, body

    def _exercise_request(path="/", headers=None):
        connection.request("GET", path, headers=headers or {})
        response = connection.getresponse()
        body = response.read()
        return response, body

    if request.param == "putrequest":
        return _exercise_putrequest
    else:
        return _exercise_request


def process_response(body):
    body = body.decode("utf-8").strip()
    values = body.splitlines()
    values = [[x.strip() for x in s.split(":", 1)] for s in values]
    return {v[0]: v[1] for v in values}


def test_httplib_request(server, exercise):
    scoped = [(f"External/localhost:{server.port}/http/", 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        (f"External/localhost:{server.port}/all", 1),
        (f"External/localhost:{server.port}/http/", 1),
    ]

    @validate_transaction_metrics(
        "test_httplib:test_httplib_request", scoped_metrics=scoped, rollup_metrics=rollup, background_task=True
    )
    @background_task(name="test_httplib:test_httplib_request")
    def _test():
        exercise()

    _test()


@pytest.mark.parametrize(
    "distributed_tracing,span_events,exclude_newrelic_header",
    (
        pytest.param(True, True, True, id="dt_on-spans_on-exclude_nr_header"),
        pytest.param(True, True, False, id="dt_on-spans_on-include_nr_header"),
        pytest.param(True, False, True, id="dt_on-spans_off-exclude_nr_header"),
        pytest.param(True, False, False, id="dt_on-spans_off-include_nr_header"),
        pytest.param(False, False, True, id="dt_off-spans_off-exclude_nr_header"),
    ),
)
def test_httplib_distributed_tracing_request(exercise, distributed_tracing, span_events, exclude_newrelic_header):
    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
            "distributed_tracing.exclude_newrelic_header": exclude_newrelic_header,
        }
    )
    @background_task(name="test_httplib:test_httplib_distributed_tracing_request")
    @cache_outgoing_headers
    @validate_distributed_tracing_headers
    def _test():
        exercise()

    _test()


def test_httplib_multiple_requests_unique_distributed_tracing_id(exercise):
    response_headers = []

    @background_task(name="test_httplib:test_transaction")
    def test_transaction():
        # make multiple requests with the same connection
        _, body = exercise()
        response_headers.append(process_response(body))
        _, body = exercise()
        response_headers.append(process_response(body))

    test_transaction = override_application_settings(
        {"distributed_tracing.enabled": True, "span_events.enabled": True}
    )(test_transaction)
    test_transaction()

    dt_payloads = [W3CTraceParent.decode(header["traceparent"]) for header in response_headers]

    # Both requests belong to the same transaction, so they must share a
    # trace id but generate unique span ids.
    trace_ids = {payload["tr"] for payload in dt_payloads}
    assert len(trace_ids) == 1, dt_payloads

    span_ids = {payload["id"] for payload in dt_payloads}
    assert len(span_ids) == len(dt_payloads), dt_payloads


@pytest.mark.parametrize("key", sorted(NR_HEADER_KEYS))
def test_httplib_nr_headers_added(exercise, key):
    value = "testval"
    headers = []

    @background_task(name="test_httplib:test_transaction")
    def test_transaction():
        _, body = exercise(headers={key: value})
        headers.append(process_response(body))

    test_transaction = override_application_settings(
        {"distributed_tracing.enabled": True, "span_events.enabled": True}
    )(test_transaction)
    test_transaction()
    # verify a DT header the caller already set is not overridden by the agent
    assert headers[0][key] == value
    other_keys = NR_HEADER_KEYS - {key}
    assert not (other_keys & headers[0].keys()), headers[0]


def test_span_events(server, exercise):
    exact_intrinsics = {
        "name": f"External/localhost:{server.port}/http/",
        "type": "Span",
        "sampled": True,
        "category": "http",
        "span.kind": "client",
        "component": "http",
    }
    exact_agents = {"http.url": server.url, "http.statusCode": 200}

    expected_intrinsics = ("timestamp", "duration", "transactionId")

    @override_application_settings({"span_events.enabled": True})
    @dt_enabled
    @validate_span_events(
        count=1, exact_intrinsics=exact_intrinsics, exact_agents=exact_agents, expected_intrinsics=expected_intrinsics
    )
    @validate_tt_segment_params(exact_params=exact_agents)
    @background_task(name="test_httplib:test_span_events")
    def _test():
        response, _ = exercise()
        assert response.status == 200

    _test()
