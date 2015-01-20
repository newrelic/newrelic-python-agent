import os
import random

import redis

from testing_support.fixtures import validate_transaction_metrics

from newrelic.agent import background_task, set_background_task

REDIS_HOST = os.environ.get('TDIUM_REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('TDIUM_REDIS_PORT', '6379'))

REDIS_HOST = os.environ.get('REDIS_PORT_6379_TCP_ADDR', REDIS_HOST)
REDIS_PORT = int(os.environ.get('REDIS_PORT_6379_TCP_PORT', REDIS_PORT))

_test_httplib_http_request_scoped_metrics = [
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1)]

_test_httplib_http_request_rollup_metrics = [
        ('Datastore/all', 2),
        ('Datastore/allWeb', 2),
        ('Datastore/Redis/all', 2),
        ('Datastore/Redis/allWeb', 2),
        ('Datastore/operation/Redis/get', 1),
        ('Datastore/operation/Redis/set', 1)]

@validate_transaction_metrics(
        'test_redis:test_redis_operation',
        scoped_metrics=_test_httplib_http_request_scoped_metrics,
        rollup_metrics=_test_httplib_http_request_rollup_metrics,
        background_task=False)
@background_task()
def test_redis_operation():
    set_background_task(False)

    r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

    r.set('key', 'value')
    r.get('key')
