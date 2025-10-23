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

import urllib.request as urllib2

import pytest
from testing_support.external_fixtures import cache_outgoing_headers
from testing_support.validators.validate_distributed_tracing_headers import validate_distributed_tracing_headers
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture(scope="session")
def metrics(server):
    scoped = [(f"External/localhost:{server.port}/urllib2/", 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        (f"External/localhost:{server.port}/all", 1),
        (f"External/localhost:{server.port}/urllib2/", 1),
    ]

    return scoped, rollup


def test_urlopen_http_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib2:test_urlopen_http_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib2:test_urlopen_http_request")
    def _test():
        urllib2.urlopen(f"http://localhost:{server.port}/")

    _test()


def test_urlopen_https_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib2:test_urlopen_https_request",
        scoped_metrics=metrics[0],
        rollup_metrics=metrics[1],
        background_task=True,
    )
    @background_task(name="test_urllib2:test_urlopen_https_request")
    def _test():
        try:
            urllib2.urlopen(f"https://localhost:{server.port}/")
        except Exception:
            pass

    _test()


def test_urlopen_http_request_with_port(server):
    scoped = [(f"External/localhost:{server.port}/urllib2/", 1)]

    rollup = [
        ("External/all", 1),
        ("External/allOther", 1),
        (f"External/localhost:{server.port}/all", 1),
        (f"External/localhost:{server.port}/urllib2/", 1),
    ]

    @validate_transaction_metrics(
        "test_urllib2:test_urlopen_http_request_with_port",
        scoped_metrics=scoped,
        rollup_metrics=rollup,
        background_task=True,
    )
    @background_task(name="test_urllib2:test_urlopen_http_request_with_port")
    def _test():
        urllib2.urlopen(f"http://localhost:{server.port}/")

    _test()


_test_urlopen_file_request_scoped_metrics = [("External/unknown/urllib2/", None)]

_test_urlopen_file_request_rollup_metrics = [
    ("External/all", None),
    ("External/allOther", None),
    ("External/unknown/urllib2/", None),
]


@validate_transaction_metrics(
    "test_urllib2:test_urlopen_file_request",
    scoped_metrics=_test_urlopen_file_request_scoped_metrics,
    rollup_metrics=_test_urlopen_file_request_rollup_metrics,
    background_task=True,
)
@background_task()
def test_urlopen_file_request():
    file_uri = f"file://{__file__}"
    urllib2.urlopen(file_uri)


@background_task()
@cache_outgoing_headers
@validate_distributed_tracing_headers
def test_urlopen_distributed_tracing_request(server):
    urllib2.urlopen(f"http://localhost:{server.port}/")
