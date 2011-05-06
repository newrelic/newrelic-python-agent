from newrelic.agent import wrap_memcache_trace

def instrument(module):
    wrap_memcache_trace(module, 'Client', 'add', 'add')
    wrap_memcache_trace(module, 'Client', 'append', 'replace')
    wrap_memcache_trace(module, 'Client', 'cas', 'replace')
    wrap_memcache_trace(module, 'Client', 'decr', 'decr')
    wrap_memcache_trace(module, 'Client', 'delete', 'delete')
    wrap_memcache_trace(module, 'Client', 'delete_multi', 'delete')
    wrap_memcache_trace(module, 'Client', 'get', 'get')
    wrap_memcache_trace(module, 'Client', 'gets', 'get')
    wrap_memcache_trace(module, 'Client', 'get_multi', 'get')
    wrap_memcache_trace(module, 'Client', 'incr', 'incr')
    wrap_memcache_trace(module, 'Client', 'prepend', 'replace')
    wrap_memcache_trace(module, 'Client', 'replace', 'replace')
    wrap_memcache_trace(module, 'Client', 'set', 'set')
    wrap_memcache_trace(module, 'Client', 'set_multi', 'set')
