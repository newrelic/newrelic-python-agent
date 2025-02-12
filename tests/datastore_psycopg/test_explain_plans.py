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

import threading

import psycopg
import pytest
from conftest import DB_SETTINGS, maybe_await
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_database_node import validate_database_node
from testing_support.validators.validate_transaction_slow_sql_count import validate_transaction_slow_sql_count

from newrelic.api.background_task import background_task
from newrelic.core.database_utils import SQLConnections


class CustomCursor(psycopg.Cursor):
    event = threading.Event()

    def execute(self, *args, **kwargs):
        self.event.set()
        return super().execute(*args, **kwargs)


class CustomAsyncCursor(psycopg.AsyncCursor):
    event = threading.Event()

    async def execute(self, *args, **kwargs):
        self.event.set()
        return await super().execute(*args, **kwargs)


class CustomConnection(psycopg.Connection):
    event = threading.Event()

    def cursor(self, *args, **kwargs):
        self.event.set()
        return super().cursor(*args, **kwargs)


class CustomAsyncConnection(psycopg.AsyncConnection):
    event = threading.Event()

    def cursor(self, *args, **kwargs):
        self.event.set()
        return super().cursor(*args, **kwargs)


def reset_events():
    # Reset all event flags
    CustomCursor.event.clear()
    CustomAsyncCursor.event.clear()
    CustomConnection.event.clear()
    CustomAsyncConnection.event.clear()


async def _exercise_db(connection, cursor_kwargs=None):
    cursor_kwargs = cursor_kwargs or {}

    try:
        cursor = connection.cursor(**cursor_kwargs)

        await maybe_await(cursor.execute("SELECT setting from pg_settings where name=%s", ("server_version",)))
    finally:
        await maybe_await(connection.close())


# Tests


def explain_plan_is_not_none(node):
    with SQLConnections() as connections:
        explain_plan = node.explain_plan(connections)

    assert explain_plan is not None


SCROLLABLE = (True, False)
WITHHOLD = (True, False)


@pytest.mark.parametrize("withhold", WITHHOLD)
@pytest.mark.parametrize("scrollable", SCROLLABLE)
@override_application_settings({"transaction_tracer.explain_threshold": 0.0, "transaction_tracer.record_sql": "raw"})
@validate_database_node(explain_plan_is_not_none)
@validate_transaction_slow_sql_count(1)
@background_task(name="test_explain_plan_unnamed_cursors")
def test_explain_plan_unnamed_cursors(loop, connection, withhold, scrollable):
    cursor_kwargs = {}

    if withhold:
        cursor_kwargs["withhold"] = withhold

    if scrollable:
        cursor_kwargs["scrollable"] = scrollable

    loop.run_until_complete(_exercise_db(connection, cursor_kwargs=cursor_kwargs))


@pytest.mark.parametrize("withhold", WITHHOLD)
@pytest.mark.parametrize("scrollable", SCROLLABLE)
@override_application_settings({"transaction_tracer.explain_threshold": 0.0, "transaction_tracer.record_sql": "raw"})
@validate_database_node(explain_plan_is_not_none)
@validate_transaction_slow_sql_count(1)
@background_task(name="test_explain_plan_named_cursors")
def test_explain_plan_named_cursors(loop, connection, withhold, scrollable):
    cursor_kwargs = {"name": "test_explain_plan_named_cursors"}

    if withhold:
        cursor_kwargs["withhold"] = withhold

    if scrollable:
        cursor_kwargs["scrollable"] = scrollable

    loop.run_until_complete(_exercise_db(connection, cursor_kwargs=cursor_kwargs))


# This test validates that any combination of sync or async, and default or custom connection and cursor classes will work with
# the explain plan feature. The agent should always use psycopg.connect to open a new explain plan connection and only
# use custom cursors from synchronous connections, as async cursors will not be compatible.
@pytest.mark.parametrize(
    "connection_cls,cursor_cls",
    [
        (psycopg.Connection, psycopg.Cursor),
        (psycopg.Connection, CustomCursor),
        (CustomConnection, psycopg.Cursor),
        (CustomConnection, CustomCursor),
        (psycopg.AsyncConnection, psycopg.AsyncCursor),
        (psycopg.AsyncConnection, CustomAsyncCursor),
        (CustomAsyncConnection, psycopg.AsyncCursor),
        (CustomAsyncConnection, CustomAsyncCursor),
    ],
)
@override_application_settings({"transaction_tracer.explain_threshold": 0.0, "transaction_tracer.record_sql": "raw"})
def test_explain_plan_on_custom_classes(loop, connection_cls, cursor_cls):
    @validate_database_node(explain_plan_is_not_none)
    @validate_transaction_slow_sql_count(1)
    @background_task(name="test_explain_plan_on_custom_connect_class")
    def test():
        async def coro():
            # Connect using custom Connection classes, so connect here without the fixture.
            connection = await maybe_await(
                connection_cls.connect(
                    dbname=DB_SETTINGS["name"],
                    user=DB_SETTINGS["user"],
                    password=DB_SETTINGS["password"],
                    host=DB_SETTINGS["host"],
                    port=DB_SETTINGS["port"],
                    cursor_factory=cursor_cls,
                )
            )
            await _exercise_db(connection)
            reset_events()

        loop.run_until_complete(coro())

    test()

    # Check that the correct classes were used AFTER the explain plan validator has run
    if hasattr(connection_cls, "event"):
        assert not connection_cls.event.is_set(), "Custom connection class should not be used."
    if hasattr(cursor_cls, "event"):
        if cursor_cls is not CustomAsyncCursor:
            assert cursor_cls.event.is_set(), "Custom cursor class was not used."
        else:
            assert not cursor_cls.event.is_set(), "Custom async cursor class should not be used."


# This test will verify that arguments are preserved for an explain
# plan by forcing a failure to be generated when explain plans are created and
# arguments are preserved
