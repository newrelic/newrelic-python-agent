import os

import memcache

try:
    import http.client as httplib
except ImportError:
    import httplib

from testing_support.fixtures import validate_transaction_metrics

from newrelic.agent import background_task, set_background_task

def _e(key, default):
    return os.environ.get(key, default)

MEMCACHED_HOST = _e('TDDIUM_MEMCACHE_HOST', 'localhost')
MEMCACHED_PORT = _e('TDDIUM_MEMCACHE_PORT', '11211')
MEMCACHED_NAMESPACE = ''

MEMCACHED_HOST = _e('MEMCACHED_PORT_11211_TCP_ADDR', MEMCACHED_HOST)
MEMCACHED_PORT = _e('MEMCACHED_PORT_11211_TCP_PORT', MEMCACHED_PORT)
MEMCACHED_NAMESPACE = _e('TDDIUM_MEMCACHE_NAMESPACE', MEMCACHED_NAMESPACE)

MEMCACHED_ADDR = '%s:%s' % (MEMCACHED_HOST, MEMCACHED_PORT)

_test_bt_set_get_delete_scoped_metrics = [
        ('Memcache/set', 1),
        ('Memcache/get', 1),
        ('Memcache/delete', 1)]

_test_bt_set_get_delete_rollup_metrics = [
        ('Memcache/all', 3),
        ('Memcache/allOther', 3),
        ('Memcache/set', 1),
        ('Memcache/get', 1),
        ('Memcache/delete', 1)]

@validate_transaction_metrics(
        'test_memcache:test_bt_set_get_delete',
        scoped_metrics=_test_bt_set_get_delete_scoped_metrics,
        rollup_metrics=_test_bt_set_get_delete_rollup_metrics,
        background_task=True)
@background_task()
def test_bt_set_get_delete():
    set_background_task(True)
    client = memcache.Client([MEMCACHED_ADDR])

    key = MEMCACHED_NAMESPACE + 'key'

    client.set(key, 'value')
    value = client.get(key)
    client.delete(key)

    assert value == 'value'

_test_wt_set_get_delete_scoped_metrics = [
        ('Memcache/set', 1),
        ('Memcache/get', 1),
        ('Memcache/delete', 1)]

_test_wt_set_get_delete_rollup_metrics = [
        ('Memcache/all', 3),
        ('Memcache/allWeb', 3),
        ('Memcache/set', 1),
        ('Memcache/get', 1),
        ('Memcache/delete', 1)]

@validate_transaction_metrics(
        'test_memcache:test_wt_set_get_delete',
        scoped_metrics=_test_wt_set_get_delete_scoped_metrics,
        rollup_metrics=_test_wt_set_get_delete_rollup_metrics,
        background_task=False)
@background_task()
def test_wt_set_get_delete():
    set_background_task(False)
    client = memcache.Client([MEMCACHED_ADDR])

    key = MEMCACHED_NAMESPACE + 'key'

    client.set(key, 'value')
    value = client.get(key)
    client.delete(key)

    assert value == 'value'
