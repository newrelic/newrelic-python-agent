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


def capture_host(self, *args, **kwargs):
    if hasattr(self, "_pool") and hasattr(self._pool, "_host"):
        return self._pool._host


def capture_port(self, *args, **kwargs):
    if hasattr(self, "_pool") and hasattr(self._pool, "_port"):
        return self._pool._port


def instrument_aiomcache_client(module):
    for name in _memcache_client_methods:
        if hasattr(module.Client, name):
            wrap_datastore_trace(
                module,
                f"Client.{name}",
                product="Memcached",
                target=None,
                operation=name,
                host=capture_host,
                port_path_or_id=capture_port,
            )
