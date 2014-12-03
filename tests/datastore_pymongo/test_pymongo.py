import os
import random
import sqlite3

import pymongo

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, validate_database_duration)
from testing_support.settings import mongodb_settings

from newrelic.agent import background_task

MONGODB_HOST, MONGODB_PORT = mongodb_settings()

def _exercise_mongo(db):
    db.my_collection.save({"x": 10})
    db.my_collection.save({"x": 8})
    db.my_collection.save({"x": 11})
    db.my_collection.find_one()

    for item in db.my_collection.find():
        item["x"]

    db.my_collection.create_index("x")

    for item in db.my_collection.find().sort("x", pymongo.ASCENDING):
        item["x"]

    [item["x"] for item in db.my_collection.find().limit(2).skip(1)]

# Common Metrics for tests that use _exercise_mongo().

_test_pymongo_scoped_metrics = [
        ('Datastore/statement/MongoDB/my_collection/save', 3),
        ('Datastore/statement/MongoDB/my_collection/create_index', 1),
        ('Datastore/statement/MongoDB/my_collection/find', 3),
        ('Datastore/statement/MongoDB/my_collection/find_one', 1)]

_test_pymongo_rollup_metrics = [
        ('Datastore/MongoDB/all', 8),
        ('Datastore/MongoDB/allOther', 8),
        ('Datastore/operation/MongoDB/save', 3),
        ('Datastore/operation/MongoDB/create_index', 1),
        ('Datastore/operation/MongoDB/find', 3),
        ('Datastore/operation/MongoDB/find_one', 1),
        ('Datastore/statement/MongoDB/my_collection/save', 3),
        ('Datastore/statement/MongoDB/my_collection/create_index', 1),
        ('Datastore/statement/MongoDB/my_collection/find', 3),
        ('Datastore/statement/MongoDB/my_collection/find_one', 1)]

# Add Connection metric

_test_pymongo_connection_scoped_metrics = (_test_pymongo_scoped_metrics +
        [('Function/pymongo.connection:Connection.__init__', 1)])

_test_pymongo_connection_rollup_metrics = (_test_pymongo_rollup_metrics +
        [('Function/pymongo.connection:Connection.__init__', 1)])

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

    cur.execute("CREATE TABLE blah (name text, quantity int)")
    cur.execute("INSERT INTO blah VALUES ('Bob', 22)")

    conn.commit()
    conn.close()
