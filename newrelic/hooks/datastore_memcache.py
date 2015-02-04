from newrelic.agent import wrap_datastore_trace

_memcache_client_methods = ('get_stats', 'get_slabs', 'flush_all',
    'delete_multi', 'delete', 'incr', 'decr', 'add', 'append', 'prepend',
    'replace', 'set', 'cas', 'sets_multi', 'get', 'gets', 'get_multi')

def instrument_memcache(module):
    for name in _memcache_client_methods:
        if hasattr(module.Client, name):
            wrap_datastore_trace(module.Client, name,
                    product='Memcached', target=None, operation=name)
