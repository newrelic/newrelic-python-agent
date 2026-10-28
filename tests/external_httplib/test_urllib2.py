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
from testing_support.fixtures import override_application_settings
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


def test_urlopen_request(server, metrics):
    @validate_transaction_metrics(
        "test_urllib2:test_urlopen_request", scoped_metrics=metrics[0], rollup_metrics=metrics[1], background_task=True
    )
    @background_task(name="test_urllib2:test_urlopen_request")
    def _test():
        urllib2.urlopen(f"{server.url}/")

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
def test_urlopen_distributed_tracing_request(server, distributed_tracing, span_events, exclude_newrelic_header):
    @override_application_settings(
        {
            "distributed_tracing.enabled": distributed_tracing,
            "span_events.enabled": span_events,
            "distributed_tracing.exclude_newrelic_header": exclude_newrelic_header,
        }
    )
    @background_task(name="test_urllib2:test_urlopen_distributed_tracing_request")
    @cache_outgoing_headers
    @validate_distributed_tracing_headers
    def _test():
        urllib2.urlopen(f"{server.url}/")

    _test()
