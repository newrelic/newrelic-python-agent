from newrelic.api.external_trace import wrap_external_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper


def _nr_wrapper_httplib2_endheaders_wrapper(*library_info):

    def _nr_wrapper_httplib2_endheaders_wrapper_inner(wrapped, instance,
            args, kwargs):

        def _connect_unbound(instance, *args, **kwargs):
            return instance

        if instance is None:
            instance = _connect_unbound(*args, **kwargs)

        connection = instance

        connection._nr_library_info = library_info
        return wrapped(*args, **kwargs)

    return _nr_wrapper_httplib2_endheaders_wrapper_inner


def instrument(module):

    wrap_function_wrapper(module, 'HTTPConnectionWithTimeout.endheaders',
            _nr_wrapper_httplib2_endheaders_wrapper('httplib2', 'http'))

    wrap_function_wrapper(module, 'HTTPSConnectionWithTimeout.endheaders',
            _nr_wrapper_httplib2_endheaders_wrapper('httplib2', 'https'))

    def url_request(connection, uri, *args, **kwargs):
        return uri

    wrap_external_trace(module, 'Http.request', 'httplib2', url_request)
