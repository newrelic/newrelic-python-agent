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
from testing_support.db_settings import mongodb_settings
from testing_support.validators.validate_database_duration import validate_database_duration
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.common import system_info

DB_SETTINGS = mongodb_settings()[0]
MONGODB_HOST = DB_SETTINGS["host"]
MONGODB_PORT = DB_SETTINGS["port"]
MONGODB_COLLECTION = DB_SETTINGS["collection"]

INSTANCE_METRIC_HOST = system_info.gethostname() if MONGODB_HOST == "127.0.0.1" else MONGODB_HOST
INSTANCE_METRIC_NAME = f"Datastore/instance/MongoDB/{INSTANCE_METRIC_HOST}/{MONGODB_PORT}"


# Find correct metric name based on import availability.
try:
    from pymongo.synchronous.mongo_client import MongoClient

    INIT_FUNCTION_METRIC = "Function/pymongo.synchronous.mongo_client:MongoClient.__init__"
except ImportError:
    from pymongo.mongo_client import MongoClient

    INIT_FUNCTION_METRIC = "Function/pymongo.mongo_client:MongoClient.__init__"


def _exercise_mongo_v3(db):
    collection = db[MONGODB_COLLECTION]

    collection.save({"x": 10})
    collection.save({"x": 8})
    collection.save({"x": 11})

    collection.find_one()
    [item["x"] for item in collection.find()]

    collection.create_index("x")

    [item["x"] for item in collection.find().sort("x", pymongo.ASCENDING)]
    [item["x"] for item in collection.find().limit(2).skip(1)]

    collection.initialize_unordered_bulk_op()
    collection.initialize_ordered_bulk_op()
    collection.parallel_scan(1)

    collection.bulk_write([pymongo.InsertOne({"x": 1})])
    collection.insert_one({"x": 300})
    collection.insert_many([{"x": 1} for i in range(20, 25)])
    collection.replace_one({"x": 1}, {"x": 2})
    collection.update_one({"x": 1}, {"$inc": {"x": 3}})
    collection.update_many({"x": 1}, {"$inc": {"x": 3}})
    collection.delete_one({"x": 4})
    collection.delete_many({"x": 4})
    collection.find_raw_batches()
    collection.create_indexes([pymongo.IndexModel([("x", pymongo.DESCENDING)])])
    collection.list_indexes()
    collection.aggregate([])
    collection.aggregate_raw_batches([])
    collection.find_one_and_delete({"x": 10})
    collection.find_one_and_replace({"x": 300}, {"x": 301})
    collection.find_one_and_update({"x": 301}, {"$inc": {"x": 300}})


def _exercise_mongo_v4(db):
    collection = db[MONGODB_COLLECTION]

    collection.insert_one({"x": 10})
    collection.insert_one({"x": 8})
    collection.insert_one({"x": 11, "y": 11})

    collection.find_one()

    [item["x"] for item in collection.find()]
    [item["x"] for item in collection.find().sort("x", pymongo.ASCENDING)]
    [item["x"] for item in collection.find().limit(2).skip(1)]

    collection.bulk_write([pymongo.InsertOne({"x": 1})])
    collection.insert_one({"x": 300})
    collection.insert_many([{"x": 1} for i in range(20, 25)])
    collection.count_documents({"x": 1})
    collection.estimated_document_count({"x": 1})
    collection.replace_one({"x": 1}, {"x": 2})
    collection.update_one({"x": 1}, {"$inc": {"x": 3}})
    collection.update_many({"x": 1}, {"$inc": {"x": 3}})
    collection.delete_one({"x": 4})
    collection.delete_many({"x": 4})
    collection.distinct(key="x")
    [item for item in collection.find_raw_batches()]

    collection.create_index("x")
    collection.create_indexes([pymongo.IndexModel([("y", pymongo.DESCENDING)])])
    [item for item in collection.list_indexes()]
    collection.index_information()
    collection.drop_index("x_1")
    collection.drop_indexes()

    [item for item in collection.aggregate([])]
    [item for item in collection.aggregate_raw_batches([])]
    collection.find_one_and_delete({"x": 10})
    collection.find_one_and_replace({"x": 300}, {"x": 301})
    collection.find_one_and_update({"x": 301}, {"$inc": {"x": 300}})
    collection.options()

    new_name = f"{MONGODB_COLLECTION}_renamed"
    collection.rename(new_name)
    db[new_name].drop()
    collection.drop()


def _exercise_mongo(db):
    if pymongo.version_tuple < (4, 0):
        _exercise_mongo_v3(db)
    else:
        _exercise_mongo_v4(db)


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
def test_collection_instance_info(loop):
    # Make mongodb query
    client = MongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client["test"]
    db[MONGODB_COLLECTION].insert_one({"x": 300})


# Common Metrics for tests that use _exercise_mongo().


_test_pymongo_scoped_metrics_v3 = [
    (INIT_FUNCTION_METRIC, 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/aggregate_raw_batches", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/aggregate", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/bulk_write", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/create_index", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/create_indexes", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/delete_many", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/delete_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one_and_delete", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one_and_replace", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one_and_update", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find_raw_batches", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/find", 3),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/initialize_ordered_bulk_op", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/initialize_unordered_bulk_op", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/insert_many", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/insert_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/list_indexes", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/parallel_scan", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/replace_one", 1),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/save", 3),
    (f"Datastore/statement/MongoDB/{MONGODB_COLLECTION}/update_one", 1),
]

_test_pymongo_rollup_metrics_v3 = [
    ("Datastore/all", 28),
    ("Datastore/allOther", 28),
    ("Datastore/MongoDB/all", 28),
    ("Datastore/MongoDB/allOther", 28),
    # We have 1 less instance metrics than Datastore/all here due to the init function
    (INSTANCE_METRIC_NAME, 27),
    ("Datastore/operation/MongoDB/aggregate_raw_batches", 1),
    ("Datastore/operation/MongoDB/aggregate", 1),
    ("Datastore/operation/MongoDB/bulk_write", 1),
    ("Datastore/operation/MongoDB/create_index", 1),
    ("Datastore/operation/MongoDB/create_indexes", 1),
    ("Datastore/operation/MongoDB/delete_many", 1),
    ("Datastore/operation/MongoDB/delete_one", 1),
    ("Datastore/operation/MongoDB/find_one_and_delete", 1),
    ("Datastore/operation/MongoDB/find_one_and_replace", 1),
    ("Datastore/operation/MongoDB/find_one_and_update", 1),
    ("Datastore/operation/MongoDB/find_one", 1),
    ("Datastore/operation/MongoDB/find_raw_batches", 1),
    ("Datastore/operation/MongoDB/find", 3),
    ("Datastore/operation/MongoDB/initialize_ordered_bulk_op", 1),
    ("Datastore/operation/MongoDB/initialize_unordered_bulk_op", 1),
    ("Datastore/operation/MongoDB/insert_many", 1),
    ("Datastore/operation/MongoDB/insert_one", 1),
    ("Datastore/operation/MongoDB/list_indexes", 1),
    ("Datastore/operation/MongoDB/parallel_scan", 1),
    ("Datastore/operation/MongoDB/replace_one", 1),
    ("Datastore/operation/MongoDB/save", 3),
    ("Datastore/operation/MongoDB/update_one", 1),
]
_test_pymongo_rollup_metrics_v3.extend(_test_pymongo_scoped_metrics_v3)


_test_pymongo_scoped_metrics_v4 = [
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

_test_pymongo_rollup_metrics_v4 = [
    ("Datastore/all", 35),
    ("Datastore/allOther", 35),
    ("Datastore/MongoDB/all", 35),
    ("Datastore/MongoDB/allOther", 35),
    # We have 1 less instance metrics than Datastore/all here due to the init function
    (INSTANCE_METRIC_NAME, 34),
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
_test_pymongo_rollup_metrics_v4.extend(_test_pymongo_scoped_metrics_v4)


def test_collection_operations():
    if pymongo.version_tuple < (4, 0):
        _test_pymongo_client_scoped_metrics = _test_pymongo_scoped_metrics_v3
        _test_pymongo_client_rollup_metrics = _test_pymongo_rollup_metrics_v3
    else:
        _test_pymongo_client_scoped_metrics = _test_pymongo_scoped_metrics_v4
        _test_pymongo_client_rollup_metrics = _test_pymongo_rollup_metrics_v4

    @validate_transaction_errors(errors=[])
    @validate_transaction_metrics(
        "test_collection_operations",
        scoped_metrics=_test_pymongo_client_scoped_metrics,
        rollup_metrics=_test_pymongo_client_rollup_metrics,
        background_task=True,
    )
    @background_task(name="test_collection_operations")
    def _test():
        client = MongoClient(MONGODB_HOST, MONGODB_PORT)
        db = client.test
        _exercise_mongo(db)

    _test()


@validate_database_duration()
@background_task()
def test_collection_mongodb_database_duration():
    client = MongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.test
    _exercise_mongo(db)


@validate_database_duration()
@background_task()
def test_collection_mongodb_and_sqlite_database_duration():
    # Make mongodb queries

    client = MongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.test
    _exercise_mongo(db)

    # Make sqlite queries

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE contacts (name text, age int)")
    cur.execute("INSERT INTO contacts VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
