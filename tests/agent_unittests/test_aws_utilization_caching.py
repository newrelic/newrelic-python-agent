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

from newrelic.common.utilization import AWSUtilization

FIXTURE = Path(__file__).parent / "aws.json"

_parameters_list = ["testname", "auth_token_cls", "uri", "expected_vendors_hash", "expected_metrics"]

_parameters = ",".join(_parameters_list)


@classmethod
def fake_token(cls):
    return "FakeToken"


@classmethod
def no_token(cls):
    return None


def _load_tests():
    with FIXTURE.open(encoding="utf-8") as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


# Load the tests from the JSON fixture
_aws_tests = [_parametrize_test(t) for t in _load_tests()]


# Order of tests:
# 1. auth token fails, no cached data
# 2. Auth token succeeds, but utilization data is invalid, no cached data
# 3. Auth token succeeds, utilization data is valid, data is cached (check both cache and returned value)
# 4. Auth token fails, but cached data is valid, return cached data
# 5. Auth token succeeds, utilization data is valid, data is cached (check both cache and returned value)


@pytest.mark.parametrize(_parameters, _aws_tests)
def test_aws_utilization_caching(monkeypatch, testname, auth_token_cls, uri, expected_vendors_hash, expected_metrics):
    def _get_mock_return_value(api_result):
        if api_result["timeout"]:
            return 0, None
        else:
            body = json.dumps(api_result["response"])
            return 200, body.encode("utf-8")

    url, api_result = uri.popitem()
    status, data = _get_mock_return_value(api_result)

    client_cls = create_client_cls(status, data, url)

    monkeypatch.setattr(AWSUtilization, "CLIENT_CLS", client_cls)
    monkeypatch.setattr(AWSUtilization, "fetchAuthToken", fake_token if auth_token_cls == "fake_token" else no_token)

    metrics = []
    if expected_metrics:
        metrics = [(k, v.get("call_count")) for k, v in expected_metrics.items()]

    # Define function that actually runs the test

    @validate_internal_metrics(metrics=metrics)
    def _test_aws_data():
        data = AWSUtilization.detect()

        if data:
            aws_vendor_hash = {"aws": data}
        else:
            aws_vendor_hash = None

        assert aws_vendor_hash == expected_vendors_hash
        if expected_vendors_hash is not None:
            # Check that the cached data is set to the most recent valid data
            assert json.loads(AWSUtilization._utilization_data.decode("utf-8")) == data

    _test_aws_data()

    assert not client_cls.FAIL
