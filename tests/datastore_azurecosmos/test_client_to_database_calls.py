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


def test_client_calls_to_database(client, database):
    database_client = client.get_database_client("test_database")
    assert database_client.id == database.id
    client.get_database_account()

    client.create_database_if_not_exists("another_database")
    all_databases = client.list_databases()
    db_ids = {db_dict.get("id") for db_dict in all_databases}
    assert db_ids == {"test_database", "another_database"}

    client.delete_database("another_database")


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


def test_client_query_databases(client, database):
    results = client.query_databases("SELECT * FROM c WHERE c.id = 'test_database'")
    assert any([db.get("id") == "test_database" for db in results])


def test_client_query_databases(loop, async_client, async_database):
    async def _test_client_query_databases():
        async_results = async_client.query_databases("SELECT * FROM c WHERE c.id = 'test_database'")
        # async for db in async_results:
        #     breakpoint()
        #     db.get("id")
        assert any([db.get("id") == "test_database" async for db in async_results])

    loop.run_until_complete(_test_client_query_databases())