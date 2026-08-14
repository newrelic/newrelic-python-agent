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


def test_database_calls(client):
    database = client.create_database(
        "database_with_throughput",
        offer_throughput=400,
    )
    database.read()
    database.replace_throughput(throughput=42)
    database.get_throughput()
    client.delete_database("database_with_throughput")


def test_async_database_calls(loop, async_client):
    async def _test_async_database_calls():
        async_database = await async_client.create_database(
            "database_with_throughput",
            offer_throughput=400,
        )
        await async_database.read()
        await async_database.replace_throughput(throughput=42)
        await async_database.get_throughput()
        await async_client.delete_database("database_with_throughput")

    loop.run_until_complete(_test_async_database_calls())


def test_database_read_offer(database):
    database.read_offer()

