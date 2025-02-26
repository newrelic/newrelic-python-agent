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
from testing_support.fixtures import reset_core_stats_engine
from testing_support.validators.validate_dimensional_metric_payload import validate_dimensional_metric_payload
from testing_support.validators.validate_metric_payload import validate_metric_payload

from newrelic.api.application import application_instance
from newrelic.api.background_task import background_task
from newrelic.api.transaction import record_custom_metric, record_dimensional_metric
from newrelic.core.rules_engine import NormalizationRule, RulesEngine

RULES = [{"match_expression": "(replace)", "replacement": "expected", "ignore": False, "eval_order": 0}]
EXPECTED_TAGS = frozenset({"tag": 1}.items())


def _prepare_rules(test_rules):
    # ensure all keys are present, if not present set to an empty string
    for rule in test_rules:
        for key in NormalizationRule._fields:
            rule[key] = rule.get(key, "")
    return test_rules


@pytest.fixture(scope="session")
def core_app(collector_agent_registration):
    app = collector_agent_registration
    return app._agent.application(app.name)


@pytest.fixture(scope="function")
def rules_engine_fixture(core_app):
    rules_engine = core_app._rules_engine
    previous_rules = rules_engine["metric"]

    rules_engine["metric"] = RulesEngine(_prepare_rules(RULES))
    yield
    rules_engine["metric"] = previous_rules  # Restore after test run


@validate_dimensional_metric_payload(summary_metrics=[("Metric/expected", EXPECTED_TAGS, 1)])
@validate_metric_payload([("Metric/expected", 1)])
@reset_core_stats_engine()
def test_metric_normalization_inside_transaction(core_app, rules_engine_fixture):
    @background_task(name="test_record_dimensional_metric_inside_transaction")
    def _test():
        record_dimensional_metric("Metric/replace", 1, tags={"tag": 1})
        record_custom_metric("Metric/replace", 1)

    _test()
    core_app.harvest()


@validate_dimensional_metric_payload(summary_metrics=[("Metric/expected", EXPECTED_TAGS, 1)])
@validate_metric_payload([("Metric/expected", 1)])
@reset_core_stats_engine()
def test_metric_normalization_outside_transaction(core_app, rules_engine_fixture):
    def _test():
        app = application_instance()
        record_dimensional_metric("Metric/replace", 1, tags={"tag": 1}, application=app)
        record_custom_metric("Metric/replace", 1, application=app)

    _test()
    core_app.harvest()
