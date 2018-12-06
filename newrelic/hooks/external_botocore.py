from newrelic.api.coroutine_trace import return_value_fn
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import (wrap_function_wrapper,
        FunctionWrapper)

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


CUSTOM_TRACE_POINTS = {
}


def bind__create_api_method(py_operation_name, operation_name, service_model):
    return (py_operation_name, operation_name, service_model)


def _nr_clientcreator__create_api_method_(wrapped, instance, args, kwargs):
    (py_operation_name, operation_name, service_model) = \
            bind__create_api_method(*args)

    api_method = wrapped(*args, **kwargs)
    service_name = service_model._service_name.lower()

    if hasattr(CUSTOM_TRACE_POINTS.get(service_name), py_operation_name):
        tracer = getattr(CUSTOM_TRACE_POINTS[service_name], py_operation_name)
        return_value = return_value_fn(wrapped)

        def wrap_service_method(_wrapped, _instance, _args, _kwargs):
            transaction = current_transaction()
            if transaction is None:
                return _wrapped(*_args, **_kwargs)

            trace = tracer(transaction, operation_name, _instance, _kwargs)
            return return_value(trace, lambda: _wrapped(*_args, **_kwargs))

        return FunctionWrapper(api_method, wrap_service_method)

    return api_method


def _nr_endpoint_make_request_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _bind_params(operation_model, request_dict, *args, **kwargs):
        return request_dict

    # Get url and strip everything but scheme, hostname, and port.

    request_dict = _bind_params(*args, **kwargs)
    full_url = request_dict.get('url', '')
    parsed = urlparse.urlparse(full_url)
    url = '%s://%s' % (parsed.scheme, parsed.netloc)

    # Get HTTP verb as method
    method = request_dict.get('method', None)

    with ExternalTrace(transaction, library='botocore', url=url,
            method=method):
        return wrapped(*args, **kwargs)


def instrument_botocore_endpoint(module):
    wrap_function_wrapper(module, 'Endpoint.make_request',
            _nr_endpoint_make_request_)


def instrument_botocore_client(module):
    wrap_function_wrapper(module, 'ClientCreator._create_api_method',
            _nr_clientcreator__create_api_method_)
