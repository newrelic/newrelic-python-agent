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

from conftest import db_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

_base_user_calls = (
    ("Datastore/all", 2),
    ("Datastore/CosmosDB/all", 2),
    ("Datastore/allOther", 2),
    ("Datastore/CosmosDB/allOther", 2),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 2),
)

_scoped_user_calls = (
    ("Datastore/operation/CosmosDB/get_user_client", 1),
    ("Datastore/operation/CosmosDB/list_users", 1),
)


@validate_transaction_metrics(
    "test_database_to_user_calls:test_database_calls_to_user",
    scoped_metrics=_scoped_user_calls,
    rollup_metrics=[*_scoped_user_calls, *_base_user_calls],
    background_task=True,
)
@background_task()
def test_database_calls_to_user(database, user):
    user_client = database.get_user_client("test_user")
    assert user_client.id == user.id

    all_users = database.list_users()
    assert any(user.get("id") == "test_user" for user in all_users)


@validate_transaction_metrics(
    "test_database_to_user_calls:test_async_database_calls_to_user",
    scoped_metrics=_scoped_user_calls,
    rollup_metrics=[*_scoped_user_calls, *_base_user_calls],
    background_task=True,
)
@background_task()
def test_async_database_calls_to_user(loop, async_database, async_user):
    async def _test_async_database_calls_to_user():
        user_client = async_database.get_user_client("test_user")
        assert user_client.id == async_user.id

        all_users = async_database.list_users()
        assert any([user.get("id") == "test_user" async for user in all_users])

    loop.run_until_complete(_test_async_database_calls_to_user())


_base_user_complete = (
    ("Datastore/all", 5),
    ("Datastore/CosmosDB/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/CosmosDB/allOther", 5),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 5),
)

_scoped_user_complete = (
    ("Datastore/operation/CosmosDB/replace_user", 1),
    ("Datastore/operation/CosmosDB/query_users", 1),
    ("Datastore/operation/CosmosDB/create_user", 1),
    ("Datastore/operation/CosmosDB/upsert_user", 1),
    ("Datastore/operation/CosmosDB/delete_user", 1),
)


@validate_transaction_metrics(
    "test_database_to_user_calls:test_database_user_complete",
    scoped_metrics=_scoped_user_complete,
    rollup_metrics=[*_scoped_user_complete, *_base_user_complete],
    background_task=True,
)
@background_task()
def test_database_user_complete(database, user):
    database.replace_user(user, {"id": "test_user"})
    database.query_users("SELECT * FROM c WHERE c.id = 'test_user'")
    database.create_user({"id": "another_user"})
    database.upsert_user({"id": "another_user"})
    database.delete_user("another_user")


@validate_transaction_metrics(
    "test_database_to_user_calls:test_async_database_user_complete",
    scoped_metrics=_scoped_user_complete,
    rollup_metrics=[*_scoped_user_complete, *_base_user_complete],
    background_task=True,
)
@background_task()
def test_async_database_user_complete(loop, async_database, async_user):
    async def _test_async_database_user_complete():
        await async_database.replace_user(async_user, {"id": "test_user"})
        async_database.query_users("SELECT * FROM c WHERE c.id = 'test_user'")
        await async_database.create_user({"id": "another_user"})
        await async_database.upsert_user({"id": "another_user"})
        await async_database.delete_user("another_user")

    loop.run_until_complete(_test_async_database_user_complete())
