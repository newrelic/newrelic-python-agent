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


def test_database_calls_to_user(database, user):
    user_client = database.get_user_client("test_user")
    assert user_client.id == user.id

    all_users = database.list_users()
    assert any([user.get("id") == "test_user" for user in all_users])


def test_async_database_calls_to_user(loop, async_database, async_user):
    async def _test_async_database_calls_to_user():
        user_client = async_database.get_user_client("test_user")
        assert user_client.id == async_user.id

        all_users = async_database.list_users()
        assert any([user.get("id") == "test_user" async for user in all_users])

    loop.run_until_complete(_test_async_database_calls_to_user())


def test_database_user_complete(database, user):
    database.replace_user(user, {"id": "test_user"})
    database.query_users("SELECT * FROM c WHERE c.id = 'test_user'")
    database.create_user({"id": "another_user"})
    database.upsert_user({"id": "another_user"})
    database.delete_user("another_user")


def test_async_database_user_complete(loop, async_database, async_user):
    async def _test_async_database_user_complete():
        async_database.replace_user(async_user, {"id": "test_user"})
        async_database.query_users("SELECT * FROM c WHERE c.id = 'test_user'")
        async_database.create_user({"id": "another_user"})
        async_database.upsert_user({"id": "another_user"})
        async_database.delete_user("another_user")

    loop.run_until_complete(_test_async_database_user_complete())

