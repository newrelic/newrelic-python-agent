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
import os

import pytest
from testing_support.validators.validate_metric_payload import validate_metric_payload

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_custom_metric
from newrelic.core.rules_engine import RulesEngine

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(CURRENT_DIR, "fixtures", "rules.json"))


def _load_tests():
    with open(FIXTURE, "r") as fh:
        js = fh.read()
    return json.loads(js)


def _make_case_insensitive(rules):
    # lowercase each rule
    for rule in rules:
        rule["match_expression"] = rule["match_expression"].lower()
        if rule.get("replacement"):
            rule["replacement"] = rule["replacement"].lower()
    return rules


@pytest.mark.parametrize("test_group", _load_tests())
def test_rules_engine(test_group):
    # FIXME: The test fixture assumes that matching is case insensitive when it
    # is not. To avoid errors, just lowercase all rules, inputs, and expected
    # values.
    test_rules = _make_case_insensitive(test_group["rules"])
    rules_engine = RulesEngine(test_rules)

    for test in test_group["tests"]:
        # lowercase each value
        input_str = test["input"].lower()
        expected = (test["expected"] or "").lower()

        result, ignored = rules_engine.normalize(input_str)

        # When a transaction is to be ignored, the test fixture expects that
        # "expected" is None.
        if ignored:
            assert expected == ""
        else:
            assert result == expected


@pytest.mark.parametrize("test_group", _load_tests())
def test_rules_engine_metric_harvest(test_group):
    # FIXME: The test fixture assumes that matching is case insensitive when it
    # is not. To avoid errors, just lowercase all rules, inputs, and expected
    # values.
    test_rules = _make_case_insensitive(test_group["rules"])
    rules_engine = RulesEngine(test_rules)

    # Set rules engine on core application
    api_application = application_instance(activate=False)
    api_name = api_application.name
    core_application = api_application._agent.application(api_name)
    old_rules = core_application._rules_engine["metric"]  # save previoius rules
    core_application._rules_engine["metric"] = rules_engine

    def send_metrics():
        # Send all metrics in this test batch in one transaction, then harvest so the normalizer is run.
        @background_task(name="send_metrics")
        def _test():
            for test in test_group["tests"]:
                # lowercase each value
                input_str = test["input"].lower()
                record_custom_metric(input_str, {"count": 1})

        _test()
        core_application.harvest()

    try:
        # Create a map of all result metrics to validate after harvest
        test_metrics = []
        for test in test_group["tests"]:
            expected = (test["expected"] or "").lower()
            if expected == "":  # Ignored
                test_metrics.append((expected, None))
            else:
                test_metrics.append((expected, 1))

        # Harvest and validate resulting payload
        validate_metric_payload(metrics=test_metrics)(send_metrics)()
    finally:
        # Replace original rules engine
        core_application._rules_engine["metric"] = old_rules
