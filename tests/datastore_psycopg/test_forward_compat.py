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

import psycopg

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.hooks.database_psycopg import wrapper_psycopg_as_string


class TestCompatability:
    def as_string(self, giraffe, lion, tiger=None):
        assert type(giraffe) in (psycopg.Cursor, psycopg.AsyncCursor)
        return "PASS"


wrap_function_wrapper(__name__, "TestCompatability.as_string", wrapper_psycopg_as_string)


def test_forward_compat_args(connection):
    cursor = connection.cursor()
    query = TestCompatability()
    result = query.as_string(cursor, "giraffe-nomming-leaves")
    assert result == "PASS"


def test_forward_compat_kwargs(connection):
    cursor = connection.cursor()
    query = TestCompatability()
    result = query.as_string(cursor, lion="eats tiger", tiger="eats giraffe")
    assert result == "PASS"
