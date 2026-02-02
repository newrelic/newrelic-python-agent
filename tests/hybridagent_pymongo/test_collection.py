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
INSTANCE_METRIC_NAME = f"Datastore/instance/mongodb/{INSTANCE_METRIC_HOST}/{MONGODB_PORT}"


# Find correct metric name based on import availability.
try:
    from pymongo.synchronous.mongo_client import MongoClient

except ImportError:
    from pymongo.mongo_client import MongoClient


def _exercise_mongo(db):
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
    list(collection.find_raw_batches())

    collection.create_index("x")
    collection.create_indexes([pymongo.IndexModel([("y", pymongo.DESCENDING)])])
    list(collection.list_indexes())
    collection.index_information()
    collection.drop_index("x_1")
    collection.drop_indexes()

    list(collection.aggregate([]))
    list(collection.aggregate_raw_batches([]))
    collection.find_one_and_delete({"x": 10})
    collection.find_one_and_replace({"x": 300}, {"x": 301})
    collection.find_one_and_update({"x": 301}, {"$inc": {"x": 300}})
    collection.options()

    new_name = f"{MONGODB_COLLECTION}_renamed"
    collection.rename(new_name)
    db[new_name].drop()
    collection.drop()


@validate_span_events(
    count=1,
    exact_agents={
        "db.operation": "insert",
        "db.collection": MONGODB_COLLECTION,
        "db.instance": "test",
        "peer.hostname": INSTANCE_METRIC_HOST,
        "peer.address": f"{INSTANCE_METRIC_HOST}:{MONGODB_PORT}",
    },
    exact_intrinsics={"name": f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/insert"},
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

_test_pymongo_client_scoped_metrics = [
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/insert", 6),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/find", 5),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/aggregate", 3),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/count", 1),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/update", 3),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/delete", 2),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/distinct", 1),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/createindexes", 2),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/listindexes", 2),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/dropindexes", 2),
    ("Datastore/operation/mongodb/getmore", 1),
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}/findandmodify", 3),
    ("Datastore/operation/mongodb/listcollections", 1),
    (
        f"Datastore/statement/mongodb/test.{MONGODB_COLLECTION}/renamecollection",
        1,
    ),  # admin commands use name given by OTel
    (f"Datastore/statement/mongodb/{MONGODB_COLLECTION}_renamed/drop", 1),
]

_test_pymongo_client_rollup_metrics = [
    ("Datastore/all", 35),
    ("Datastore/allOther", 35),
    ("Datastore/mongodb/all", 35),
    ("Datastore/mongodb/allOther", 35),
    (INSTANCE_METRIC_NAME, 35),
    ("Datastore/operation/mongodb/insert", 6),
    ("Datastore/operation/mongodb/find", 5),
    ("Datastore/operation/mongodb/aggregate", 3),
    ("Datastore/operation/mongodb/count", 1),
    ("Datastore/operation/mongodb/update", 3),
    ("Datastore/operation/mongodb/delete", 2),
    ("Datastore/operation/mongodb/distinct", 1),
    ("Datastore/operation/mongodb/createindexes", 2),
    ("Datastore/operation/mongodb/listindexes", 2),
    ("Datastore/operation/mongodb/dropindexes", 2),
    ("Datastore/operation/mongodb/findandmodify", 3),
    ("Datastore/operation/mongodb/renamecollection", 1),
]
_test_pymongo_client_rollup_metrics.extend(_test_pymongo_client_scoped_metrics)


def test_collection_operations(tracer_provider):
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
