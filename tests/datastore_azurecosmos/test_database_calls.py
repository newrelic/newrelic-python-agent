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

from conftest import _IDENTIFIER, db_settings
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task

_base_database_read = (
    ("Datastore/all", 5),
    ("Datastore/CosmosDB/all", 5),
    ("Datastore/allOther", 5),
    ("Datastore/CosmosDB/allOther", 5),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 5),
)

_scoped_database_read = (
    ("Datastore/operation/CosmosDB/create_database", 1),
    ("Datastore/operation/CosmosDB/read", 1),
    ("Datastore/operation/CosmosDB/replace_throughput", 1),
    ("Datastore/operation/CosmosDB/get_throughput", 1),
    ("Datastore/operation/CosmosDB/delete_database", 1),
)


@validate_transaction_metrics(
    "test_database_calls:test_database_calls",
    scoped_metrics=_scoped_database_read,
    rollup_metrics=[*_scoped_database_read, *_base_database_read],
    background_task=True,
)
@background_task()
def test_database_calls(client):
    db_name = f"database_with_throughput_{_IDENTIFIER}"
    database = client.create_database(db_name, offer_throughput=400)
    database.read()
    database.replace_throughput(throughput=42)
    database.get_throughput()
    client.delete_database(db_name)


@validate_transaction_metrics(
    "test_database_calls:test_async_database_calls",
    scoped_metrics=_scoped_database_read,
    rollup_metrics=[*_scoped_database_read, *_base_database_read],
    background_task=True,
)
@background_task()
def test_async_database_calls(loop, async_client):
    async def _test_async_database_calls():
        db_name = f"database_with_throughput_{_IDENTIFIER}"
        async_database = await async_client.create_database(db_name, offer_throughput=400)
        await async_database.read()
        await async_database.replace_throughput(throughput=42)
        await async_database.get_throughput()
        await async_client.delete_database(db_name)

    loop.run_until_complete(_test_async_database_calls())


# NOTE: This command has already been deprecated
# so it will eventually need a conditional skip.
_base_database_read_offer = (
    ("Datastore/all", 1),
    ("Datastore/CosmosDB/all", 1),
    ("Datastore/allOther", 1),
    ("Datastore/CosmosDB/allOther", 1),
    (f"Datastore/instance/CosmosDB/{db_settings()}", 1),
)

_scoped_database_read_offer = (("Datastore/operation/CosmosDB/read_offer", 1),)


@validate_transaction_metrics(
    "test_database_calls:test_database_read_offer",
    scoped_metrics=_scoped_database_read_offer,
    rollup_metrics=[*_scoped_database_read_offer, *_base_database_read_offer],
    background_task=True,
)
@background_task()
def test_database_read_offer(database):
    database.read_offer()
