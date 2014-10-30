import os
import random

import pymongo

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors)

from newrelic.agent import background_task

MONGODB_HOST = os.environ.get('TDIUM_MONGOID_HOST', 'localhost')
MONGODB_PORT = int(os.environ.get('TDIUM_MONGOID_PORT', '27017'))

MONGODB_HOST = os.environ.get('MONGODB_PORT_27017_TCP_ADDR', MONGODB_HOST)
MONGODB_PORT = int(os.environ.get('MONGODB_PORT_27017_TCP_PORT', MONGODB_PORT))

_test_httplib_http_request_scoped_metrics = [
        ('Function/pymongo.connection:Connection.__init__', 1),
        ('Datastore/statement/MongoDB/my_collection/save', 3),
        ('Datastore/statement/MongoDB/my_collection/create_index', 1),
        ('Datastore/statement/MongoDB/my_collection/find', 3),
        ('Datastore/statement/MongoDB/my_collection/find_one', 1)]

_test_httplib_http_request_rollup_metrics = [
        ('Function/pymongo.connection:Connection.__init__', 1),
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

@validate_transaction_errors(errors=[])
@validate_transaction_metrics(
        'test_pymongo:test_mongodb_operation',
        scoped_metrics=_test_httplib_http_request_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_rollup_metrics,
        background_task=True)
@background_task()
def test_mongodb_operation():
    connection = pymongo.Connection(MONGODB_HOST, MONGODB_PORT)

    db = connection.test

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
