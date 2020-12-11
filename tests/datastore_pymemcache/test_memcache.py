import os

import pymemcache.client

from testing_support.fixtures import validate_transaction_metrics
from testing_support.db_settings import memcached_settings

from newrelic.api.background_task import background_task
from newrelic.api.transaction import set_background_task

DB_SETTINGS = memcached_settings()[0]

MEMCACHED_HOST = DB_SETTINGS["host"]
MEMCACHED_PORT = DB_SETTINGS["port"]
MEMCACHED_NAMESPACE = DB_SETTINGS["namespace"]

MEMCACHED_ADDR = (MEMCACHED_HOST, int(MEMCACHED_PORT))

_test_bt_set_get_delete_scoped_metrics = [
        ('Datastore/operation/Memcached/set', 1),
        ('Datastore/operation/Memcached/get', 1),
        ('Datastore/operation/Memcached/delete', 1)]

_test_bt_set_get_delete_rollup_metrics = [
        ('Datastore/all', 3),
        ('Datastore/allOther', 3),
        ('Datastore/Memcached/all', 3),
        ('Datastore/Memcached/allOther', 3),
        ('Datastore/operation/Memcached/set', 1),
        ('Datastore/operation/Memcached/get', 1),
        ('Datastore/operation/Memcached/delete', 1)]

@validate_transaction_metrics(
        'test_memcache:test_bt_set_get_delete',
        scoped_metrics=_test_bt_set_get_delete_scoped_metrics,
        rollup_metrics=_test_bt_set_get_delete_rollup_metrics,
        background_task=True)
@background_task()
def test_bt_set_get_delete():
    set_background_task(True)
    client = pymemcache.client.Client(MEMCACHED_ADDR)

    key = MEMCACHED_NAMESPACE + 'key'

    client.set(key, b'value')
    value = client.get(key)
    client.delete(key)

    assert value == b'value'

_test_wt_set_get_delete_scoped_metrics = [
        ('Datastore/operation/Memcached/set', 1),
        ('Datastore/operation/Memcached/get', 1),
        ('Datastore/operation/Memcached/delete', 1)]

_test_wt_set_get_delete_rollup_metrics = [
        ('Datastore/all', 3),
        ('Datastore/allWeb', 3),
        ('Datastore/Memcached/all', 3),
        ('Datastore/Memcached/allWeb', 3),
        ('Datastore/operation/Memcached/set', 1),
        ('Datastore/operation/Memcached/get', 1),
        ('Datastore/operation/Memcached/delete', 1)]

@validate_transaction_metrics(
        'test_memcache:test_wt_set_get_delete',
        scoped_metrics=_test_wt_set_get_delete_scoped_metrics,
        rollup_metrics=_test_wt_set_get_delete_rollup_metrics,
        background_task=False)
@background_task()
def test_wt_set_get_delete():
    set_background_task(False)
    client = pymemcache.client.Client(MEMCACHED_ADDR)

    key = MEMCACHED_NAMESPACE + 'key'

    client.set(key, b'value')
    value = client.get(key)
    client.delete(key)

    assert value == b'value'
