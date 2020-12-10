import memcache
from newrelic.hooks.datastore_memcache import (_memcache_client_methods,
        _memcache_multi_methods)

def test_all_methods_wrapped():
    client = memcache.Client([])

    all_methods = (list(_memcache_client_methods) +
            list(_memcache_multi_methods))

    for m in all_methods:
        method = getattr(client, m)
        assert hasattr(method, '__wrapped__')
