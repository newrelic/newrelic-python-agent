from newrelic.api.message_trace import message_trace
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


def extract(argument_names, default=None):
    def extractor(*args, **kwargs):
        for argument_name in argument_names:
            argument_value = kwargs.get(argument_name)
            if argument_value:
                return argument_value

        return default

    return extractor


CUSTOM_TRACE_POINTS = {
    ('sns', 'publish'): message_trace(
            'SimpleNotificationService', 'Produce', 'Topic',
            extract(('TopicArn', 'TargetArn'), 'PhoneNumber')),
}


def bind__create_api_method(py_operation_name, operation_name, service_model,
        *args, **kwargs):
    return (py_operation_name, service_model)


def _nr_clientcreator__create_api_method_(wrapped, instance, args, kwargs):
    (py_operation_name, service_model) = \
            bind__create_api_method(*args, **kwargs)

    service_name = service_model.service_name.lower()
    tracer = CUSTOM_TRACE_POINTS.get((service_name, py_operation_name))

    wrapped = wrapped(*args, **kwargs)

    if not tracer:
        return wrapped

    return tracer(wrapped)


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
