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

try:
    from psycopg import sql
except ImportError:
    sql = None

from newrelic.api.background_task import background_task


@background_task()
def test_as_string_1(connection):
    # All of these are similar to those described in the doctests in
    # psycopg/lib/sql.py

    comp = sql.Composed([sql.SQL("insert into "), sql.Identifier("table")])
    result = comp.as_string(connection)
    assert result == 'insert into "table"'


@background_task()
def test_as_string_2(connection):
    fields = sql.Identifier("foo") + sql.Identifier("bar")  # a Composed
    result = fields.join(", ").as_string(connection)
    assert result == '"foo", "bar"'


@background_task()
def test_as_string_3(connection):
    query = sql.SQL("select {0} from {1}").format(
        sql.SQL(", ").join([sql.Identifier("foo"), sql.Identifier("bar")]), sql.Identifier("table")
    )
    result = query.as_string(connection)
    assert result == 'select "foo", "bar" from "table"'


@background_task()
def test_as_string_4(connection):
    result = (
        sql.SQL("select * from {0} where {1} = %s")
        .format(sql.Identifier("people"), sql.Identifier("id"))
        .as_string(connection)
    )
    assert result == 'select * from "people" where "id" = %s'


@background_task()
def test_as_string_5(connection):
    result = (
        sql.SQL("select * from {tbl} where {pkey} = %s")
        .format(tbl=sql.Identifier("people"), pkey=sql.Identifier("id"))
        .as_string(connection)
    )
    assert result == 'select * from "people" where "id" = %s'


@background_task()
def test_as_string_6(connection):
    snip = sql.SQL(", ").join(sql.Identifier(n) for n in ["foo", "bar", "baz"])
    result = snip.as_string(connection)
    assert result == '"foo", "bar", "baz"'


@background_task()
def test_as_string_7(connection):
    t1 = sql.Identifier("foo")
    t2 = sql.Identifier("ba'r")
    t3 = sql.Identifier('ba"z')
    result = sql.SQL(", ").join([t1, t2, t3]).as_string(connection)
    assert result == '"foo", "ba\'r", "ba""z"'


@background_task()
def test_as_string_8(connection):
    s1 = sql.Literal("foo")
    s2 = sql.Literal("ba'r")
    s3 = sql.Literal(42)
    result = sql.SQL(", ").join([s1, s2, s3]).as_string(connection)
    assert result == "'foo', 'ba''r', 42"


@background_task()
def test_as_string_9(connection):
    names = ["foo", "bar", "baz"]
    q1 = sql.SQL("insert into table ({0}) values ({1})").format(
        sql.SQL(", ").join(map(sql.Identifier, names)), sql.SQL(", ").join(sql.Placeholder() * len(names))
    )
    result = q1.as_string(connection)
    assert result == 'insert into table ("foo", "bar", "baz") values (%s, %s, %s)'


@background_task()
def test_as_string_10(connection):
    names = ["foo", "bar", "baz"]
    q2 = sql.SQL("insert into table ({0}) values ({1})").format(
        sql.SQL(", ").join(map(sql.Identifier, names)), sql.SQL(", ").join(map(sql.Placeholder, names))
    )
    result = q2.as_string(connection)
    assert result == 'insert into table ("foo", "bar", "baz") values (%(foo)s, %(bar)s, %(baz)s)'
