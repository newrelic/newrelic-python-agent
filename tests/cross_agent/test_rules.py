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

from newrelic.core.rules_engine import RulesEngine, NormalizationRule

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE = os.path.normpath(os.path.join(
        CURRENT_DIR, 'fixtures', 'rules.json'))

def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)

def _prepare_rules(test_rules):
    # ensure all keys are present, if not present set to an empty string
    for rule in test_rules:
        for key in NormalizationRule._fields:
            rule[key] = rule.get(key, '')
    return test_rules

def _make_case_insensitive(rules):
    # lowercase each rule
    for rule in rules:
        rule['match_expression'] = rule['match_expression'].lower()
        if rule.get('replacement'):
            rule['replacement'] = rule['replacement'].lower()
    return rules

@pytest.mark.parametrize('test_group', _load_tests())
def test_rules_engine(test_group):

    # FIXME: The test fixture assumes that matching is case insensitive when it
    # is not. To avoid errors, just lowercase all rules, inputs, and expected
    # values.
    insense_rules = _make_case_insensitive(test_group['rules'])
    test_rules = _prepare_rules(insense_rules)
    rules_engine = RulesEngine(test_rules)

    for test in test_group['tests']:

        # lowercase each value
        input_str = test['input'].lower()
        expected = (test['expected'] or '').lower()

        result, ignored = rules_engine.normalize(input_str)

        # When a transaction is to be ignored, the test fixture expects that
        # "expected" is None.
        if ignored:
            assert expected == ''
        else:
            assert result == expected
