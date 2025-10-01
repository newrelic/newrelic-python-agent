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
from testing_support.fixtures import Environ
from testing_support.validators.validate_internal_metrics import validate_internal_metrics

from newrelic.common.utilization import PCFUtilization

FIXTURE = Path(__file__).parent / "fixtures" / "utilization_vendor_specific" / "pcf.json"

_parameters_list = ["testname", "env_vars", "expected_vendors_hash", "expected_metrics"]

_parameters = ",".join(_parameters_list)


def _load_tests():
    with FIXTURE.open(encoding="utf-8") as fh:
        js = fh.read()
    return json.loads(js)


def _parametrize_test(test):
    return tuple([test.get(f, None) for f in _parameters_list])


_pcf_tests = [_parametrize_test(t) for t in _load_tests()]


class MockResponse:
    def __init__(self, code, body):
        self.code = code
        self.text = body

    def raise_for_status(self):
        assert str(self.code) == "200"

    def json(self):
        return self.text


@pytest.mark.parametrize(_parameters, _pcf_tests)
def test_pcf(testname, env_vars, expected_vendors_hash, expected_metrics):
    metrics = []
    if expected_metrics:
        metrics = [(k, v.get("call_count")) for k, v in expected_metrics.items()]

    @validate_internal_metrics(metrics=metrics)
    def _test_pcf_data():
        env_dict = {key: val["response"] for key, val in env_vars.items()}

        with Environ(env_dict):
            data = PCFUtilization.detect()

        if data:
            pcf_vendor_hash = {"pcf": data}
        else:
            pcf_vendor_hash = None

        assert pcf_vendor_hash == expected_vendors_hash

    _test_pcf_data()
