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
import psycopg2
from psycopg2 import extensions as ext
from utils import DB_SETTINGS
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.hooks.database_psycopg2 import wrapper_psycopg2_as_string


class TestCompatability(object):
    def as_string(self, giraffe, lion, tiger=None):
        assert isinstance(giraffe, ext.cursor)
        return "PASS"

wrap_function_wrapper(__name__, 'TestCompatability.as_string',
    wrapper_psycopg2_as_string)


@pytest.fixture(scope='module')
def conn():
    conn = psycopg2.connect(
            database=DB_SETTINGS['name'], user=DB_SETTINGS['user'],
            password=DB_SETTINGS['password'], host=DB_SETTINGS['host'],
            port=DB_SETTINGS['port'])
    yield conn
    conn.close()


def test_forward_compat_args(conn):
    cursor = conn.cursor()
    query = TestCompatability()
    result = query.as_string(cursor, 'giraffe-nomming-leaves')
    assert result == 'PASS'


def test_forward_compat_kwargs(conn):
    cursor = conn.cursor()
    query = TestCompatability()
    result = query.as_string(cursor, lion='eats tiger', tiger='eats giraffe')
    assert result == 'PASS'
