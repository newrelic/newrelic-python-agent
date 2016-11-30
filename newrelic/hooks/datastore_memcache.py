from newrelic.agent import (wrap_object, transient_function_wrapper,
        FunctionWrapper, DatastoreTrace, FunctionTrace,current_transaction)

def memcache_single_transient(dt, module, object_path):
    @transient_function_wrapper(module, object_path)
    def _nr_memcache_single_transient_(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        if len(result)>0:
            server = result[0]
            dt.host = server.ip
            dt.port_path_or_id = str(server.port)
        return result
    return _nr_memcache_single_transient_

def MemcacheSingleWrapper(wrapped, product, target, operation, module):

    def _nr_datastore_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        dt = DatastoreTrace(transaction, product, target, operation)

        @memcache_single_transient(dt, module.Client, '_get_server')
        def call_trace():
            with dt:
                return wrapped(*args, **kwargs)

        return call_trace()

    return FunctionWrapper(wrapped, _nr_datastore_trace_wrapper_)

def memcache_multi_transient(transaction, product, target,
        module, object_path):

    @transient_function_wrapper(module, object_path)
    def _nr_memcache_multi_transient_(_wrapped, _instance, _args, _kwargs):
        host = _instance.ip
        port_path_or_id = str(_instance.port)
        with DatastoreTrace(transaction, product, target, object_path,
                host = host, port_path_or_id = port_path_or_id):
            return _wrapped(*_args, **_kwargs)

    return _nr_memcache_multi_transient_

def MemcacheMultiWrapper(wrapped, product, target, operation, module):

    def _nr_function_trace_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        @memcache_multi_transient(transaction, product, target,
                module._Host, 'send_cmds')
        @memcache_multi_transient(transaction, product, target,
                module._Host, 'send_cmd')
        def call_trace():
            with FunctionTrace(transaction, operation):
                return wrapped(*args, **kwargs)

        return call_trace()

    return FunctionWrapper(wrapped, _nr_function_trace_wrapper_)

def wrap_memcache_single(module, object_path, product, target, operation):
    wrap_object(module.Client, object_path, MemcacheSingleWrapper,
            (product, target, operation, module))

def wrap_memcache_multi(module, object_path, product, target, operation):
    wrap_object(module.Client, object_path, MemcacheMultiWrapper,
            (product, target, operation, module))

_memcache_client_methods = ('delete', 'incr', 'decr', 'add',
    'append', 'prepend', 'replace', 'set', 'cas', 'get', 'gets')

_memcache_multi_methods = ('delete_multi', 'get_multi', 'set_multi',
    'get_stats', 'get_slabs', 'flush_all')


def instrument_memcache(module):
    for name in _memcache_client_methods:
        if hasattr(module.Client, name):
            wrap_memcache_single(module, name,
                    product='Memcached', target=None, operation=name)

    for name in _memcache_multi_methods:
        if hasattr(module.Client, name):
            wrap_memcache_multi(module, name,
                    product='Memcached', target=None, operation=name)
