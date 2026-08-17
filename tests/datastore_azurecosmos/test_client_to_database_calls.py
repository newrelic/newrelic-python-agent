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

from newrelic.api.background_task import background_task
from conftest import db_settings

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

_base_database_calls = (
    ("Datastore/all", 5),
    ("Datastore/CosmosDB/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/CosmosDB/allOther", 5),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 5),
)

_scoped_database_calls = (
    ("Datastore/operation/CosmosDB/get_database_client", 1),
    ("Datastore/operation/CosmosDB/create_database_if_not_exists", 1),
    ("Datastore/operation/CosmosDB/list_databases", 1),
    ("Datastore/operation/CosmosDB/delete_database", 1),
)

_scoped_sync_database_calls = (
    ("Datastore/operation/CosmosDB/get_database_account", 1),
    *_scoped_database_calls,
)

@validate_transaction_metrics(
    "test_client_to_database_calls:test_client_calls_to_database",
    scoped_metrics=_scoped_sync_database_calls,
    rollup_metrics=[*_base_database_calls, *_scoped_sync_database_calls],
    background_task=True,
)
@background_task()
def test_client_calls_to_database(client, database):
    database_client = client.get_database_client("test_database")
    assert database_client.id == database.id
    client.get_database_account()

    client.create_database_if_not_exists("another_database")
    all_databases = client.list_databases()
    db_ids = {db_dict.get("id") for db_dict in all_databases}
    assert db_ids == {"test_database", "another_database"}

    client.delete_database("another_database")


_scoped_async_database_calls = (
    ("Datastore/operation/CosmosDB/_get_database_account", 1),
    *_scoped_database_calls,
)

@validate_transaction_metrics(
    "test_client_to_database_calls:test_async_client_calls_to_database",
    scoped_metrics=_scoped_async_database_calls,
    rollup_metrics=[*_base_database_calls, *_scoped_async_database_calls],
    background_task=True,
)
@background_task()
def test_async_client_calls_to_database(loop, async_client, async_database):
    async def _test_async_client_calls_to_database():
        database_client = async_client.get_database_client("test_database")
        assert database_client.id == async_database.id

        await async_client.create_database_if_not_exists("another_database")
        all_databases = async_client.list_databases()
        await async_client._get_database_account()
        db_ids = {db_dict.get("id") async for db_dict in all_databases}
        
        assert db_ids == {"test_database", "another_database"}

        await async_client.delete_database("another_database")

    loop.run_until_complete(_test_async_client_calls_to_database())


_base_database_calls = (
    ("Datastore/all", 1),
    ("Datastore/CosmosDB/all", 1),
    ("Datastore/allOther", 1),
    ("Datastore/CosmosDB/allOther", 1),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 1),
)

_scoped_database_calls = (
    ("Datastore/operation/CosmosDB/query_databases", 1),
)

@validate_transaction_metrics(
    "test_client_to_database_calls:test_client_query_databases",
    scoped_metrics=_scoped_database_calls,
    rollup_metrics=[*_base_database_calls, *_scoped_database_calls],
    background_task=True,
)
@background_task()
def test_client_query_databases(client, database):
    results = client.query_databases("SELECT * FROM c WHERE c.id = 'test_database'")
    assert any(db.get("id") == "test_database" for db in results)


@validate_transaction_metrics(
    "test_client_to_database_calls:test_async_client_query_databases",
    scoped_metrics=_scoped_database_calls,
    rollup_metrics=[*_base_database_calls, *_scoped_database_calls],
    background_task=True,
)
@background_task()
def test_async_client_query_databases(loop, async_client, async_database):
    async def _test_async_client_query_databases():
        async_results = async_client.query_databases("SELECT * FROM c WHERE c.id = 'test_database'")
        assert any([db.get("id") == "test_database" async for db in async_results])

    loop.run_until_complete(_test_async_client_query_databases())