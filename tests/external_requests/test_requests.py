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
import requests.exceptions
from testing_support.external_fixtures import (
    cache_outgoing_headers,
    insert_incoming_headers,
)
from testing_support.fixtures import (
    cat_enabled,
    override_application_settings,
    validate_transaction_errors,
    validate_transaction_metrics,
    validate_tt_parenting,
)
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers,
)
from testing_support.validators.validate_external_node_params import (
    validate_external_node_params,
)

from newrelic.api.background_task import background_task


def get_requests_version():
    return tuple(map(int, requests.__version__.split(".")[:2]))


@pytest.fixture(scope="session")
def metrics(server):
    scoped = [("External/localhost:%d/requests/" % server.port, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("External/localhost:%d/requests/" % server.port, 1),
    ]

    return scoped, rollup


_test_requests_http_request_get_parenting = (
    "TransactionNode",
    [
        ("ExternalNode", []),
    ],
)


def test_http_request_get(server, metrics):
    @validate_tt_parenting(_test_requests_http_request_get_parenting)
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_requests:test_http_request_get",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_requests:test_http_request_get")
    def _test():
        requests.get("http://localhost:%d/" % server.port)

    _test()


@pytest.mark.skipif(get_requests_version() < (0, 8), reason="Can't set verify=False for requests.get() in v0.7")
def test_https_request_get(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_requests:test_https_request_get",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_requests:test_https_request_get")
    def _test():
        try:
            requests.get("https://localhost:%d/" % server.port, verify=False)
        except Exception:
            pass

    _test()


@pytest.mark.skipif(get_requests_version() < (1, 0), reason="Session.send() doesn't exist for requests < v1.0.")
def test_http_session_send(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_requests:test_http_session_send",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_requests:test_http_session_send")
    def _test():
        session = requests.Session()
        req = requests.Request("GET", "http://localhost:%d/" % server.port)
        prep_req = req.prepare()
        session.send(prep_req)

    _test()


_test_requests_none_url_scoped_metrics = [("External/unknown/requests/", 1)]

_test_requests_none_url_rollup_metrics = [
    ("External/all", 1),
    ("External/allOther", 1),
    ("External/unknown/all", 1),
    ("External/unknown/requests/", 1),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_requests:test_none_url_get",
    scoped_metrics=_test_requests_none_url_scoped_metrics,
    rollup_metrics=_test_requests_none_url_rollup_metrics,
    background_task=True,
)
@background_task()
def test_none_url_get():
    try:
        requests.get(None)
    except requests.exceptions.MissingSchema:
        # Python 2.
        pass
    except TypeError:
        # Python 3.
        pass


_test_requests_wrong_datatype_url_scoped_metrics = [("External/unknown.url/requests/", 1)]

_test_requests_wrong_datatype_url_rollup_metrics = [
    ("External/all", 1),
    ("External/allOther", 1),
    ("External/unknown.url/all", 1),
    ("External/unknown.url/requests/", 1),
]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
    "test_requests:test_wrong_datatype_url_get",
    scoped_metrics=_test_requests_wrong_datatype_url_scoped_metrics,
    rollup_metrics=_test_requests_wrong_datatype_url_rollup_metrics,
    background_task=True,
)
@background_task()
def test_wrong_datatype_url_get():
    try:
        requests.get({"a": 1})
    except Exception:
        pass


@pytest.mark.parametrize(
    "distributed_tracing,span_events",
    (
        (True, True),
        (True, False),
        (False, False),
    ),
)
def test_requests_cross_process_request(distributed_tracing, span_events, server):
    @validate_transaction_errors(errors=[])
    @background_task(name="test_requests:test_requests_cross_process_request")
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        requests.get("http://localhost:%d/" % server.port)

    _test = override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "cross_application_tracer.enabled": not distributed_tracing,
            "span_events.enabled": span_events,
        }
    )(_test)

    _test()


@cat_enabled
def test_requests_cross_process_response(server):
    _test_requests_cross_process_response_scoped_metrics = [
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1)
    ]

    _test_requests_cross_process_response_rollup_metrics = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("ExternalApp/localhost:%d/1#2/all" % server.port, 1),
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1),
    ]

    _test_requests_cross_process_response_external_node_params = [
        ("cross_process_id", "1#2"),
        ("external_txn_name", "test"),
        ("transaction_guid", "0123456789012345"),
    ]

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_requests:test_requests_cross_process_response",
        scoped_metrics=_test_requests_cross_process_response_scoped_metrics,
        rollup_metrics=_test_requests_cross_process_response_rollup_metrics,
        background_task=True,
    )
    @insert_incoming_headers
    @validate_external_node_params(params=_test_requests_cross_process_response_external_node_params)
    @background_task(name="test_requests:test_requests_cross_process_response")
    def _test():
        requests.get("http://localhost:%d/" % server.port)

    _test()
