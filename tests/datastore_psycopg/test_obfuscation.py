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
from conftest import DB_SETTINGS, maybe_await
from testing_support.validators.validate_database_node import validate_database_node
from testing_support.validators.validate_sql_obfuscation import validate_sql_obfuscation

from newrelic.api.background_task import background_task
from newrelic.core.database_utils import SQLConnections


@pytest.fixture()
def cursor(loop, connection):
    try:
        cursor = connection.cursor()

        loop.run_until_complete(maybe_await(cursor.execute(f"drop table if exists {DB_SETTINGS['table_name']}")))
        loop.run_until_complete(
            maybe_await(cursor.execute(f"create table {DB_SETTINGS['table_name']} (b text, c text)"))
        )

        yield cursor

    finally:
        loop.run_until_complete(maybe_await(connection.close()))


_quoting_style_tests = [
    (f"SELECT * FROM {DB_SETTINGS['table_name']} WHERE b='2'", f"SELECT * FROM {DB_SETTINGS['table_name']} WHERE b=?"),
    (
        f"SELECT * FROM {DB_SETTINGS['table_name']} WHERE b=$func$2$func$",
        f"SELECT * FROM {DB_SETTINGS['table_name']} WHERE b=?",
    ),
    (
        f"SELECT * FROM {DB_SETTINGS['table_name']} WHERE b=U&'2'",
        f"SELECT * FROM {DB_SETTINGS['table_name']} WHERE b=U&?",
    ),
]


@pytest.mark.parametrize("sql,obfuscated", _quoting_style_tests)
def test_obfuscation_quoting_styles(loop, cursor, sql, obfuscated):
    @validate_sql_obfuscation([obfuscated])
    @background_task()
    def test():
        loop.run_until_complete(maybe_await(cursor.execute(sql)))

    test()


_parameter_tests = [
    (f"SELECT * FROM {DB_SETTINGS['table_name']} where b=%s", f"SELECT * FROM {DB_SETTINGS['table_name']} where b=%s")
]


@pytest.mark.parametrize("sql,obfuscated", _parameter_tests)
def test_obfuscation_parameters(loop, cursor, sql, obfuscated):
    @validate_sql_obfuscation([obfuscated])
    @background_task()
    def test():
        loop.run_until_complete(maybe_await(cursor.execute(sql, ("hello",))))

    test()


def no_explain_plan(node):
    sql_connections = SQLConnections()
    explain_plan = node.explain_plan(sql_connections)
    assert explain_plan is None


def any_length_explain_plan(node):
    if node.statement.operation != "select":
        return

    sql_connections = SQLConnections()
    explain_plan = node.explain_plan(sql_connections)
    assert explain_plan and len(explain_plan) > 0


_test_explain_plans = [
    (
        f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']} ; SELECT (b, c) FROM {DB_SETTINGS['table_name']}",
        no_explain_plan,
    ),
    (
        f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']} ; SELECT (b, c) FROM {DB_SETTINGS['table_name']};",
        no_explain_plan,
    ),
    (f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']} WHERE b=';'", no_explain_plan),
    (f";SELECT (b, c) FROM {DB_SETTINGS['table_name']}", no_explain_plan),
    (f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']}", any_length_explain_plan),
    (f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']};", any_length_explain_plan),
    (f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']};;;;;;", any_length_explain_plan),
    (f"SELECT (b, c) FROM  {DB_SETTINGS['table_name']};\n\n", any_length_explain_plan),
]


@pytest.mark.parametrize("sql,validator", _test_explain_plans)
def test_obfuscation_explain_plans(loop, connection, sql, validator):
    @validate_database_node(validator)
    @background_task()
    async def test():
        try:
            cursor = connection.cursor()
            await maybe_await(cursor.execute(f"drop table if exists {DB_SETTINGS['table_name']}"))
            await maybe_await(cursor.execute(f"create table {DB_SETTINGS['table_name']} (b text, c text)"))

            await maybe_await(cursor.execute(sql))

        finally:
            await maybe_await(connection.commit())
            await maybe_await(connection.close())

    loop.run_until_complete(test())
