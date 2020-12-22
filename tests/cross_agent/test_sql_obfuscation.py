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

from newrelic.core.database_utils import SQLStatement


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures',
    'sql_obfuscation'))

_parameters_list = ['obfuscated', 'dialects', 'sql', 'pathological']
_parameters = ','.join(_parameters_list)


def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'sql_obfuscation.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = tuple([test.get(param, None) for param in _parameters_list])
        result.append(values)

    return result


_quoting_styles = {
    'sqlite': 'single',
    'mysql': 'single+double',
    'postgres': 'single+dollar',
    'oracle': 'single+oracle',
    'cassandra': 'single',
}


def get_quoting_styles(dialects):
    return set([_quoting_styles.get(dialect) for dialect in dialects])


class DummyDB(object):
    def __init__(self, quoting_style):
        self.quoting_style = quoting_style


@pytest.mark.parametrize(_parameters, load_tests())
def test_sql_obfuscation(obfuscated, dialects, sql, pathological):

    if pathological:
        pytest.skip()

    quoting_styles = get_quoting_styles(dialects)

    for quoting_style in quoting_styles:
        database = DummyDB(quoting_style)
        statement = SQLStatement(sql, database)
        actual_obfuscated = statement.obfuscated
        assert actual_obfuscated in obfuscated
