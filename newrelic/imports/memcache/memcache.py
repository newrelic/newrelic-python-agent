from newrelic.agent import wrap_memcache_trace

def instrument(module):

    if hasattr(module.Client, 'add'):
        wrap_memcache_trace(module, 'Client.add', 'add')
    if hasattr(module.Client, 'append'):
        wrap_memcache_trace(module, 'Client.append', 'replace')
    if hasattr(module.Client, 'cas'):
        wrap_memcache_trace(module, 'Client.cas', 'replace')
    if hasattr(module.Client, 'decr'):
        wrap_memcache_trace(module, 'Client.decr', 'decr')
    if hasattr(module.Client, 'delete'):
        wrap_memcache_trace(module, 'Client.delete', 'delete')
    if hasattr(module.Client, 'delete_multi'):
        wrap_memcache_trace(module, 'Client.delete_multi', 'delete')
    if hasattr(module.Client, 'get'):
        wrap_memcache_trace(module, 'Client.get', 'get')
    if hasattr(module.Client, 'gets'):
        wrap_memcache_trace(module, 'Client.gets', 'get')
    if hasattr(module.Client, 'get_multi'):
        wrap_memcache_trace(module, 'Client.get_multi', 'get')
    if hasattr(module.Client, 'incr'):
        wrap_memcache_trace(module, 'Client.incr', 'incr')
    if hasattr(module.Client, 'prepend'):
        wrap_memcache_trace(module, 'Client.prepend', 'replace')
    if hasattr(module.Client, 'replace'):
        wrap_memcache_trace(module, 'Client.replace', 'replace')
    if hasattr(module.Client, 'set'):
        wrap_memcache_trace(module, 'Client.set', 'set')
    if hasattr(module.Client, 'set_multi'):
        wrap_memcache_trace(module, 'Client.set_multi', 'set')
