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

import os

import pytest

try:
    import urllib.request as urllib
except:
    import urllib

from testing_support.external_fixtures import (
    cache_outgoing_headers,
    insert_incoming_headers,
)
from testing_support.fixtures import cat_enabled, validate_transaction_metrics
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers,
)
from testing_support.validators.validate_external_node_params import (
    validate_external_node_params,
)

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def metrics(server):
    scoped = [("External/localhost:%d/urllib/" % server.port, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("External/localhost:%d/urllib/" % server.port, 1),
    ]

    return scoped, rollup


def test_urlopener_http_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib:test_urlopener_http_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib:test_urlopener_http_request")
    def _test():
        opener = urllib.URLopener()
        opener.open("http://localhost:%d/" % server.port)

    _test()


def test_urlopener_https_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib:test_urlopener_https_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib:test_urlopener_https_request")
    def _test():
        opener = urllib.URLopener()
        try:
            opener.open("https://localhost:%d/" % server.port)
        except Exception:
            pass

    _test()


def test_urlopener_http_request_with_port(server):
    scoped = [("External/localhost:%d/urllib/" % server.port, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("External/localhost:%d/urllib/" % server.port, 1),
    ]

    @validate_transaction_metrics(
        "test_urllib:test_urlopener_http_request_with_port",
        scoped_metrics=scoped,
        rollup_metrics=rollup,
        background_task=True,
    )
    @background_task(name="test_urllib:test_urlopener_http_request_with_port")
    def _test():
        opener = urllib.URLopener()
        opener.open("http://localhost:%d/" % server.port)

    _test()


_test_urlopener_file_request_scoped_metrics = [("External/unknown/urllib/", None)]

_test_urlopener_file_request_rollup_metrics = [
    ("External/all", None),
    ("External/allOther", None),
    ("External/unknown/urllib/", None),
]


@validate_transaction_metrics(
    "test_urllib:test_urlopener_file_request",
    scoped_metrics=_test_urlopener_file_request_scoped_metrics,
    rollup_metrics=_test_urlopener_file_request_rollup_metrics,
    background_task=True,
)
@background_task()
def test_urlopener_file_request():
    filename = os.path.join("file://", __file__)
    opener = urllib.URLopener()
    opener.open(filename)


@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_urlopener_cross_process_request(server):
    opener = urllib.URLopener()
    opener.open("http://localhost:%d/" % server.port)


@cat_enabled
def test_urlopener_cross_process_response(server):
    _test_urlopener_cross_process_response_scoped_metrics = [
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1)
    ]

    _test_urlopener_cross_process_response_rollup_metrics = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("ExternalApp/localhost:%d/1#2/all" % server.port, 1),
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1),
    ]

    _test_urlopener_cross_process_response_external_node_params = [
        ("cross_process_id", "1#2"),
        ("external_txn_name", "test"),
        ("transaction_guid", "0123456789012345"),
    ]

    @validate_transaction_metrics(
        "test_urllib:test_urlopener_cross_process_response",
        scoped_metrics=_test_urlopener_cross_process_response_scoped_metrics,
        rollup_metrics=_test_urlopener_cross_process_response_rollup_metrics,
        background_task=True,
    )
    @insert_incoming_headers
    @validate_external_node_params(params=_test_urlopener_cross_process_response_external_node_params)
    @background_task(name="test_urllib:test_urlopener_cross_process_response")
    def _test():
        opener = urllib.URLopener()
        opener.open("http://localhost:%d/" % server.port)

    _test()


def test_urlretrieve_http_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib:test_urlretrieve_http_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib:test_urlretrieve_http_request")
    def _test():
        urllib.urlretrieve("http://localhost:%d/" % server.port)

    _test()


def test_urlretrieve_https_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib:test_urlretrieve_https_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib:test_urlretrieve_https_request")
    def _test():
        try:
            urllib.urlretrieve("https://localhost:%d/" % server.port)
        except Exception:
            pass

    _test()


@background_task()
@cache_outgoing_headers
@validate_cross_process_headers
def test_urlretrieve_cross_process_request(server):
    urllib.urlretrieve("http://localhost:%d/" % server.port)


@cat_enabled
def test_urlretrieve_cross_process_response(server):
    _test_urlretrieve_cross_process_response_scoped_metrics = [
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1)
    ]

    _test_urlretrieve_cross_process_response_rollup_metrics = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("ExternalApp/localhost:%d/1#2/all" % server.port, 1),
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1),
    ]

    _test_urlretrieve_cross_process_response_external_node_params = [
        ("cross_process_id", "1#2"),
        ("external_txn_name", "test"),
        ("transaction_guid", "0123456789012345"),
    ]

    @validate_transaction_metrics(
        "test_urllib:test_urlretrieve_cross_process_response",
        scoped_metrics=_test_urlretrieve_cross_process_response_scoped_metrics,
        rollup_metrics=_test_urlretrieve_cross_process_response_rollup_metrics,
        background_task=True,
    )
    @insert_incoming_headers
    @validate_external_node_params(params=_test_urlretrieve_cross_process_response_external_node_params)
    @background_task(name="test_urllib:test_urlretrieve_cross_process_response")
    def _test():
        urllib.urlretrieve("http://localhost:%d/" % server.port)

    _test()
