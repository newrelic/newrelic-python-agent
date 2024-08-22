from newrelic.api.datastore_trace import wrap_datastore_trace

_memcache_client_methods = (
    "get",
    "gets",
    "get_multi",
    "set",
    "cas",
    "set_multi",
    "add",
    "replace",
    "delete",
    "delete_multi",
    "incr",
    "decr",
    "flush_all",
    "stats",
)


def instrument_aiomcache_client(module):
    for name in _memcache_client_methods:
        if hasattr(module.Client, name):
            wrap_datastore_trace(module, f"Client.{name}", product="Memcached", target=None, operation=name)
