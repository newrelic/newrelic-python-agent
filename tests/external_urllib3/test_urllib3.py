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
import urllib3
import urllib3.connectionpool

try:
    import urllib3.connection
except ImportError:
    pass

from testing_support.external_fixtures import (
    cache_outgoing_headers,
    insert_incoming_headers,
)
from testing_support.fixtures import (
    cat_enabled,
    override_application_settings,
)
from testing_support.util import version2tuple
from testing_support.validators.validate_cross_process_headers import (
    validate_cross_process_headers,
)
from testing_support.validators.validate_external_node_params import (
    validate_external_node_params,
)
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def metrics(server):
    scoped = [("External/localhost:%d/urllib3/" % server.port, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("External/localhost:%d/urllib3/" % server.port, 1),
    ]

    return scoped, rollup


def test_http_request_connection_pool_urlopen(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_http_request_connection_pool_urlopen",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib3:test_http_request_connection_pool_urlopen")
    def _test():
        pool = urllib3.HTTPConnectionPool("localhost:%d" % server.port)
        pool.urlopen("GET", "/")

    _test()


def test_http_request_connection_pool_request(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_http_request_connection_pool_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib3:test_http_request_connection_pool_request")
    def _test():
        pool = urllib3.HTTPConnectionPool("localhost:%d" % server.port)
        pool.request("GET", "/")

    _test()


def test_http_request_connection_from_url_request(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_http_request_connection_from_url_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib3:test_http_request_connection_from_url_request")
    def _test():
        conn = urllib3.connection_from_url("http://localhost:%d" % server.port)
        conn.request("GET", "/")

    _test()


def test_http_request_pool_manager_urlopen(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_http_request_pool_manager_urlopen",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib3:test_http_request_pool_manager_urlopen")
    def _test():
        pool = urllib3.PoolManager(5)
        pool.urlopen("GET", "http://localhost:%d/" % server.port)

    _test()


def test_https_request_connection_pool_urlopen(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_https_request_connection_pool_urlopen",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib3:test_https_request_connection_pool_urlopen")
    def _test():
        # Setting retries to 0 so that metrics are recorded only once
        pool = urllib3.HTTPSConnectionPool("localhost:%d" % server.port, retries=0)
        try:
            pool.urlopen("GET", "/")
        except Exception:
            pass

    _test()


def test_https_request_connection_pool_request(server, metrics):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_https_request_connection_pool_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib3:test_https_request_connection_pool_request")
    def _test():
        # Setting retries to 0 so that metrics are recorded only once
        pool = urllib3.HTTPSConnectionPool("localhost:%d" % server.port, retries=0)
        try:
            pool.request("GET", "/")
        except Exception:
            pass

    _test()


def test_port_included(server):
    scoped = [("External/localhost:%d/urllib3/" % server.port, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("External/localhost:%d/urllib3/" % server.port, 1),
    ]

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_port_included", scoped_metrics=scoped, rollup_metrics=rollup, background_task=True
    )
    @background_task(name="test_urllib3:test_port_included")
    def _test():
        conn = urllib3.connection_from_url("http://localhost:%d" % server.port)
        conn.request("GET", "/")

    _test()


# Starting in urllib3 1.8, urllib3 wrote their own version of the
# HTTPConnection class. Previously the httplib/http.client HTTPConnection class
# was used. We test httplib in a different test directory so we skip this test.
@pytest.mark.skipif(
    version2tuple(urllib3.__version__) < (1, 8), reason="urllib3.connection.HTTPConnection added in 1.8"
)
def test_HTTPConnection_port_included(server):
    scoped = [("External/localhost:%d/urllib3/" % server.port, 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("External/localhost:%d/urllib3/" % server.port, 1),
    ]

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_HTTPConnection_port_included",
        scoped_metrics=scoped,
        rollup_metrics=rollup,
        background_task=True,
    )
    @background_task(name="test_urllib3:test_HTTPConnection_port_included")
    def _test():
        conn = urllib3.connection.HTTPConnection("localhost:%d" % server.port)
        conn.request("GET", "/")

    _test()


@pytest.mark.parametrize(
    "distributed_tracing,span_events",
    (
        (True, True),
        (True, False),
        (False, False),
    ),
)
def test_urlopen_cross_process_request(distributed_tracing, span_events, server):
    @validate_transaction_errors(errors=[])
    @background_task(name="test_urllib3:test_urlopen_cross_process_request")
    @cache_outgoing_headers
    @validate_cross_process_headers
    def _test():
        pool = urllib3.HTTPConnectionPool("localhost:%d" % server.port)
        pool.urlopen("GET", "/")

    _test = override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "cross_application_tracer.enabled": not distributed_tracing,
            "span_events.enabled": span_events,
        }
    )(_test)

    _test()


@cat_enabled
def test_urlopen_cross_process_response(server):
    _test_urlopen_cross_process_response_scoped_metrics = [
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1)
    ]

    _test_urlopen_cross_process_response_rollup_metrics = [
        ("External/all", 1),
        ("External/allOther", 1),
        ("External/localhost:%d/all" % server.port, 1),
        ("ExternalApp/localhost:%d/1#2/all" % server.port, 1),
        ("ExternalTransaction/localhost:%d/1#2/test" % server.port, 1),
    ]

    _test_urlopen_cross_process_response_external_node_params = [
        ("cross_process_id", "1#2"),
        ("external_txn_name", "test"),
        ("transaction_guid", "0123456789012345"),
    ]

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_urllib3:test_urlopen_cross_process_response",
        scoped_metrics=_test_urlopen_cross_process_response_scoped_metrics,
        rollup_metrics=_test_urlopen_cross_process_response_rollup_metrics,
        background_task=True,
    )
    @insert_incoming_headers
    @validate_external_node_params(params=_test_urlopen_cross_process_response_external_node_params)
    @background_task(name="test_urllib3:test_urlopen_cross_process_response")
    def _test():
        pool = urllib3.HTTPConnectionPool("localhost:%d" % server.port)
        pool.urlopen("GET", "/")

    _test()
