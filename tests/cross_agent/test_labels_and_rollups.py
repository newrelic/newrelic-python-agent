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

from newrelic.config import _process_labels_setting, _map_labels
from newrelic.core.config import global_settings

from testing_support.fixtures import override_application_settings

FIXTURE = os.path.join(os.curdir, 'fixtures', 'labels.json')

def _load_tests():
    with open(FIXTURE, 'r') as fh:
        js = fh.read()
    return json.loads(js)

def _parametrize_test(test):

    # pytest.mark.parametrize expects each test to be a tuple

    return tuple([test['name'], test['labelString'],
            test['warning'], test['expected']])

_labels_tests = [_parametrize_test(t) for t in _load_tests()]

@pytest.mark.parametrize('name,labelString,warning,expected', _labels_tests)
def test_labels(name, labelString, warning, expected):

    parsed_labels = _map_labels(labelString)
    _process_labels_setting(parsed_labels)

    settings = global_settings()

    sorted_labels = sorted(settings.labels, key=lambda x: x['label_type'])
    sorted_expected = sorted(expected, key=lambda x: x['label_type'])

    assert sorted_labels == sorted_expected
