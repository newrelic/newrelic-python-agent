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

import pymongo
import pytest
import sqlite3

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)
from testing_support.db_settings import mongodb_settings
from testing_support.validators.validate_database_duration import validate_database_duration

from newrelic.api.background_task import background_task


DB_SETTINGS = mongodb_settings()[0]
MONGODB_HOST = DB_SETTINGS["host"]
MONGODB_PORT = DB_SETTINGS["port"]
MONGODB_COLLECTION = DB_SETTINGS["collection"]


def _exercise_mongo(db):
    db[MONGODB_COLLECTION].save({"x": 10})
    db[MONGODB_COLLECTION].save({"x": 8})
    db[MONGODB_COLLECTION].save({"x": 11})
    db[MONGODB_COLLECTION].find_one()

    for item in db[MONGODB_COLLECTION].find():
        item["x"]

    db[MONGODB_COLLECTION].create_index("x")

    for item in db[MONGODB_COLLECTION].find().sort("x", pymongo.ASCENDING):
        item["x"]

    [item["x"] for item in db[MONGODB_COLLECTION].find().limit(2).skip(1)]

    if pymongo.version_tuple >= (3, 0):
        db[MONGODB_COLLECTION].initialize_unordered_bulk_op()
        db[MONGODB_COLLECTION].initialize_ordered_bulk_op()
        db[MONGODB_COLLECTION].bulk_write([pymongo.InsertOne({'x': 1})])
        db[MONGODB_COLLECTION].insert_one({'x': 300})
        db[MONGODB_COLLECTION].insert_many([{'x': 1} for i in range(20, 25)])
        db[MONGODB_COLLECTION].replace_one({'x': 1}, {'x': 2})
        db[MONGODB_COLLECTION].update_one({'x': 1}, {'$inc': {'x': 3}})
        db[MONGODB_COLLECTION].update_many({'x': 1}, {'$inc': {'x': 3}})
        db[MONGODB_COLLECTION].delete_one({'x': 4})
        db[MONGODB_COLLECTION].delete_many({'x': 4})
        db[MONGODB_COLLECTION].find_raw_batches()
        db[MONGODB_COLLECTION].parallel_scan(1)
        db[MONGODB_COLLECTION].create_indexes(
                [pymongo.IndexModel([('x', pymongo.DESCENDING)])])
        db[MONGODB_COLLECTION].list_indexes()
        db[MONGODB_COLLECTION].aggregate([])
        db[MONGODB_COLLECTION].aggregate_raw_batches([])
        db[MONGODB_COLLECTION].find_one_and_delete({'x': 10})
        db[MONGODB_COLLECTION].find_one_and_replace({'x': 300}, {'x': 301})
        db[MONGODB_COLLECTION].find_one_and_update({'x': 301}, {'$inc': {'x': 300}})


# Common Metrics for tests that use _exercise_mongo().

_all_count = 9
if pymongo.version_tuple >= (3, 0):
    _all_count += 19

_test_pymongo_scoped_metrics = [
        ('Datastore/statement/MongoDB/%s/save' % MONGODB_COLLECTION, 3),
        ('Datastore/statement/MongoDB/%s/create_index' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find' % MONGODB_COLLECTION, 3),
        ('Datastore/statement/MongoDB/%s/find_one' % MONGODB_COLLECTION, 1)]

_test_pymongo_rollup_metrics = [
        ('Datastore/all', _all_count),
        ('Datastore/allOther', _all_count),
        ('Datastore/MongoDB/all', _all_count),
        ('Datastore/MongoDB/allOther', _all_count),
        ('Datastore/operation/MongoDB/save', 3),
        ('Datastore/operation/MongoDB/create_index', 1),
        ('Datastore/operation/MongoDB/find', 3),
        ('Datastore/operation/MongoDB/find_one', 1),
        ('Datastore/statement/MongoDB/%s/save' % MONGODB_COLLECTION, 3),
        ('Datastore/statement/MongoDB/%s/create_index' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find' % MONGODB_COLLECTION, 3),
        ('Datastore/statement/MongoDB/%s/find_one' % MONGODB_COLLECTION, 1)]

if pymongo.version_tuple >= (3, 0):
    _test_pymongo_scoped_metrics.extend([
        (('Datastore/statement/MongoDB/%s' % MONGODB_COLLECTION +
                '/initialize_unordered_bulk_op'), 1),
        (('Datastore/statement/MongoDB/%s' % MONGODB_COLLECTION +
                '/initialize_ordered_bulk_op'), 1),
        ('Datastore/statement/MongoDB/%s/bulk_write' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/insert_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/insert_many' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/replace_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/update_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/delete_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/delete_many' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_raw_batches' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/parallel_scan' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/create_indexes' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/list_indexes' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/aggregate' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/aggregate_raw_batches' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_one_and_delete' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_one_and_replace' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_one_and_update' % MONGODB_COLLECTION, 1),
    ])
    _test_pymongo_rollup_metrics.extend([
        ('Datastore/operation/MongoDB/initialize_unordered_bulk_op', 1),
        ('Datastore/operation/MongoDB/initialize_ordered_bulk_op', 1),
        ('Datastore/operation/MongoDB/bulk_write', 1),
        ('Datastore/operation/MongoDB/insert_one', 1),
        ('Datastore/operation/MongoDB/insert_many', 1),
        ('Datastore/operation/MongoDB/replace_one', 1),
        ('Datastore/operation/MongoDB/update_one', 1),
        ('Datastore/operation/MongoDB/delete_one', 1),
        ('Datastore/operation/MongoDB/delete_many', 1),
        ('Datastore/operation/MongoDB/find_raw_batches', 1),
        ('Datastore/operation/MongoDB/parallel_scan', 1),
        ('Datastore/operation/MongoDB/create_indexes', 1),
        ('Datastore/operation/MongoDB/list_indexes', 1),
        ('Datastore/operation/MongoDB/aggregate', 1),
        ('Datastore/operation/MongoDB/aggregate_raw_batches', 1),
        ('Datastore/operation/MongoDB/find_one_and_delete', 1),
        ('Datastore/operation/MongoDB/find_one_and_replace', 1),
        ('Datastore/operation/MongoDB/find_one_and_update', 1),
        (('Datastore/statement/MongoDB/%s' % MONGODB_COLLECTION +
                '/initialize_unordered_bulk_op'), 1),
        (('Datastore/statement/MongoDB/%s' % MONGODB_COLLECTION +
                '/initialize_ordered_bulk_op'), 1),
        ('Datastore/statement/MongoDB/%s/bulk_write' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/insert_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/insert_many' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/replace_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/update_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/delete_one' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/delete_many' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_raw_batches' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/parallel_scan' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/create_indexes' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/list_indexes' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/aggregate' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/aggregate_raw_batches' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_one_and_delete' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_one_and_replace' % MONGODB_COLLECTION, 1),
        ('Datastore/statement/MongoDB/%s/find_one_and_update' % MONGODB_COLLECTION, 1),
    ])

# Add Connection metric

_test_pymongo_connection_scoped_metrics = (_test_pymongo_scoped_metrics +
        [('Function/pymongo.connection:Connection.__init__', 1)])

_test_pymongo_connection_rollup_metrics = (_test_pymongo_rollup_metrics +
        [('Function/pymongo.connection:Connection.__init__', 1)])


@pytest.mark.skipif(pymongo.version_tuple >= (3, 0),
        reason='PyMongo version does not have pymongo.Connection.')
@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_pymongo:test_mongodb_connection_operation',
        scoped_metrics=_test_pymongo_connection_scoped_metrics,
        rollup_metrics=_test_pymongo_connection_rollup_metrics,
        background_task=True)
@background_task()
def test_mongodb_connection_operation():
    connection = pymongo.Connection(MONGODB_HOST, MONGODB_PORT)
    db = connection.test
    _exercise_mongo(db)


# Add MongoClient metric

_test_pymongo_mongo_client_scoped_metrics = (_test_pymongo_scoped_metrics +
        [('Function/pymongo.mongo_client:MongoClient.__init__', 1)])

_test_pymongo_mongo_client_rollup_metrics = (_test_pymongo_rollup_metrics +
        [('Function/pymongo.mongo_client:MongoClient.__init__', 1)])


@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_pymongo:test_mongodb_mongo_client_operation',
        scoped_metrics=_test_pymongo_mongo_client_scoped_metrics,
        rollup_metrics=_test_pymongo_mongo_client_rollup_metrics,
        background_task=True)
@background_task()
def test_mongodb_mongo_client_operation():
    client = pymongo.MongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.test
    _exercise_mongo(db)


@validate_database_duration()
@background_task()
def test_mongodb_database_duration():
    client = pymongo.MongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.test
    _exercise_mongo(db)


@validate_database_duration()
@background_task()
def test_mongodb_and_sqlite_database_duration():

    # Make mongodb queries

    client = pymongo.MongoClient(MONGODB_HOST, MONGODB_PORT)
    db = client.test
    _exercise_mongo(db)

    # Make sqlite queries

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    cur.execute("CREATE TABLE contacts (name text, age int)")
    cur.execute("INSERT INTO contacts VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
