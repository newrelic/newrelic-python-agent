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

import json
from pathlib import Path

import pytest
from testing_support.mock_http_client import create_client_cls
from testing_support.validators.validate_internal_metrics import validate_internal_metrics

from newrelic.common.utilization import GCPUtilization

FIXTURE = Path(__file__).parent / "fixtures" / "utilization_vendor_specific" / "gcp.json"

_parameters_list = ["testname", "uri", "expected_vendors_hash", "expected_metrics"]

_parameters = ",".join(_parameters_list)


def _load_tests():
    with FIXTURE.open() as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_gcp_tests = [_parametrize_test(t) for t in _load_tests()]


@pytest.mark.parametrize(_parameters, _gcp_tests)
def test_gcp(monkeypatch, testname, uri, expected_vendors_hash, expected_metrics):
    # Generate mock responses for HttpClient

    def _get_mock_return_value(api_result):
        if api_result["timeout"]:
            return 0, None
        else:
            body = json.dumps(api_result["response"])
            return 200, body.encode("utf-8")

    url, api_result = uri.popitem()
    status, data = _get_mock_return_value(api_result)

    client_cls = create_client_cls(status, data, url)

    monkeypatch.setattr(GCPUtilization, "CLIENT_CLS", client_cls)

    metrics = []
    if expected_metrics:
        metrics = [(k, v.get("call_count")) for k, v in expected_metrics.items()]

    # Define function that actually runs the test

    @validate_internal_metrics(metrics=metrics)
    def _test_gcp_data():
        data = GCPUtilization.detect()

        if data:
            gcp_vendor_hash = {"gcp": data}
        else:
            gcp_vendor_hash = None

        assert gcp_vendor_hash == expected_vendors_hash

    _test_gcp_data()

    assert not client_cls.FAIL
