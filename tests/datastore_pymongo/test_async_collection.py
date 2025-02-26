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

import sqlite3

import pymongo
import pytest
from testing_support.db_settings import mongodb_settings
from testing_support.validators.validate_database_duration import validate_database_duration
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common import system_info
from newrelic.common.package_version_utils import get_package_version_tuple

# Skip if AsyncMongoClient has not been implemented yet
if get_package_version_tuple("pymongo") < (4, 9, 0):
    pytest.skip(allow_module_level=True, reason="AsyncMongoClient not available.")

from pymongo.asynchronous.mongo_client import AsyncMongoClient

DB_SETTINGS = mongodb_settings()[0]
MONGODB_HOST = DB_SETTINGS["host"]
MONGODB_PORT = DB_SETTINGS["port"]
MONGODB_COLLECTION = DB_SETTINGS["collection"]

INSTANCE_METRIC_HOST = system_info.gethostname() if MONGODB_HOST == "127.0.0.1" else MONGODB_HOST
INSTANCE_METRIC_NAME = f"Datastore/instance/MongoDB/{INSTANCE_METRIC_HOST}/{MONGODB_PORT}"

INIT_FUNCTION_METRIC = "Function/pymongo.asynchronous.mongo_client:AsyncMongoClient.__init__"


async def _exercise_mongo(db):
    collection = db[MONGODB_COLLECTION]

    await collection.insert_one({"x": 10})
    await collection.insert_one({"x": 8})
    await collection.insert_one({"x": 11, "y": 11})

    await collection.find_one()

    [item["x"] async for item in collection.find()]
    [item["x"] async for item in collection.find().sort("x", pymongo.ASCENDING)]
    [item["x"] async for item in collection.find().limit(2).skip(1)]

    await collection.bulk_write([pymongo.InsertOne({"x": 1})])
    await collection.insert_one({"x": 300})
    await collection.insert_many([{"x": 1} for i in range(20, 25)])
    await collection.count_documents({"x": 1})
    await collection.estimated_document_count({"x": 1})
    await collection.replace_one({"x": 1}, {"x": 2})
    await collection.update_one({"x": 1}, {"$inc": {"x": 3}})
    await collection.update_many({"x": 1}, {"$inc": {"x": 3}})
    await collection.delete_one({"x": 4})
    await collection.delete_many({"x": 4})
    await collection.distinct(key="x")
    [item async for item in collection.find_raw_batches()]

    await collection.create_index("x")
    await collection.create_indexes([pymongo.IndexModel([("y", pymongo.DESCENDING)])])
    await collection.list_indexes()
    await collection.index_information()
    await collection.drop_index("x_1")
    await collection.drop_indexes()

    await collection.aggregate([])
    await collection.aggregate_raw_batches([])
    await collection.find_one_and_delete({"x": 10})
    await collection.find_one_and_replace({"x": 300}, {"x": 301})
    await collection.find_one_and_update({"x": 301}, {"$inc": {"x": 300}})
    await collection.options()

    new_name = f"{MONGODB_COLLECTION}_renamed"
    await collection.rename(new_name)
    await db[new_name].drop()
    await collection.drop()


@validate_span_events(
    count=1,
    exact_agents={
        "db.operation": "insert_one",
        "db.collection": MONGODB_COLLECTION,
        "db.instance": "test",
        "peer.hostname": INSTANCE_METRIC_HOST,
        "peer.address": f"{INSTANCE_METRIC_HOST}:{MONGODB_PORT}",
    },
    exact_intrinsics={"name": f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/insert_one"},
)
@validate_transaction_metrics(
    "test_motor_instance_info", rollup_metrics=[(INSTANCE_METRIC_NAME, 1)], background_task=True
)
@background_task(name="test_motor_instance_info")
def test_async_collection_instance_info(loop):
    async def _test():
        # Make mongodb query
        client = AsyncMongoClient(MONGODB_HOST, MONGODB_PORT)
        db = client["test"]
        await db[MONGODB_COLLECTION].insert_one({"x": 300})

    loop.run_until_complete(_test())


# Common Metrics for tests that use _exercise_mongo().

_test_pymongo_scoped_metrics = [
    (INIT_FUNCTION_METRIC, 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/aggregate_raw_batches", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/aggregate", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/bulk_write", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/count_documents", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/create_index", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/create_indexes", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/delete_many", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/delete_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/distinct", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/drop_index", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/drop_indexes", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/drop", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}_renamed/drop", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/estimated_document_count", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one_and_delete", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one_and_replace", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one_and_update", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_raw_batches", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find", 3),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/index_information", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/insert_many", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/insert_one", 4),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/list_indexes", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/options", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/rename", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/replace_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/update_many", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/update_one", 1),
]

_test_pymongo_rollup_metrics = [
    ("Datastore/all", 35),
    ("Datastore/allOther", 35),
    ("Datastore/MongoDB/all", 35),
    ("Datastore/MongoDB/allOther", 35),
    # We have 1 less instance metrics than Datastore/all here due to the init function
    # (INSTANCE_METRIC_NAME, 34),
    ("Datastore/operation/MongoDB/aggregate_raw_batches", 1),
    ("Datastore/operation/MongoDB/aggregate", 1),
    ("Datastore/operation/MongoDB/bulk_write", 1),
    ("Datastore/operation/MongoDB/count_documents", 1),
    ("Datastore/operation/MongoDB/create_index", 1),
    ("Datastore/operation/MongoDB/create_indexes", 1),
    ("Datastore/operation/MongoDB/delete_many", 1),
    ("Datastore/operation/MongoDB/delete_one", 1),
    ("Datastore/operation/MongoDB/distinct", 1),
    ("Datastore/operation/MongoDB/drop_index", 1),
    ("Datastore/operation/MongoDB/drop_indexes", 1),
    ("Datastore/operation/MongoDB/drop", 2),
    ("Datastore/operation/MongoDB/estimated_document_count", 1),
    ("Datastore/operation/MongoDB/find_one_and_delete", 1),
    ("Datastore/operation/MongoDB/find_one_and_replace", 1),
    ("Datastore/operation/MongoDB/find_one_and_update", 1),
    ("Datastore/operation/MongoDB/find_one", 1),
    ("Datastore/operation/MongoDB/find_raw_batches", 1),
    ("Datastore/operation/MongoDB/find", 3),
    ("Datastore/operation/MongoDB/index_information", 1),
    ("Datastore/operation/MongoDB/insert_many", 1),
    ("Datastore/operation/MongoDB/insert_one", 4),
    ("Datastore/operation/MongoDB/list_indexes", 1),
    ("Datastore/operation/MongoDB/options", 1),
    ("Datastore/operation/MongoDB/rename", 1),
    ("Datastore/operation/MongoDB/replace_one", 1),
    ("Datastore/operation/MongoDB/update_many", 1),
    ("Datastore/operation/MongoDB/update_one", 1),
]
_test_pymongo_rollup_metrics.extend(_test_pymongo_scoped_metrics)


def test_async_collection_operations(loop):
    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_async_collection_operations",
        scoped_metrics=_test_pymongo_scoped_metrics,
        rollup_metrics=_test_pymongo_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_async_collection_operations")
    def _test():
        client = AsyncMongoClient(MONGODB_HOST, MONGODB_PORT)
        db = client.MyDatabase
        loop.run_until_complete(_exercise_mongo(db))

    _test()


@validate_database_duration()
@background_task()
def test_async_collection_mongodb_database_duration(loop):
    client = AsyncMongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.MyDatabase
    loop.run_until_complete(_exercise_mongo(db))


@validate_database_duration()
@background_task()
def test_async_collection_mongodb_and_sqlite_database_duration(loop):
    # Make mongodb queries

    client = AsyncMongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.MyDatabase
    loop.run_until_complete(_exercise_mongo(db))

    # Make sqlite queries

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE contacts (name text, age int)")
    cur.execute("INSERT INTO contacts VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
