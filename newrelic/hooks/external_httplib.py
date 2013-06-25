from newrelic.agent import (ExternalTrace, ObjectWrapper, current_transaction)

def httplib_connect_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    parent = transaction._parent_node()

    # Already wrapped - return right away.

    if not parent or parent.terminal_node():
        return wrapped(*args, **kwargs)

    connection = instance

    with ExternalTrace(transaction, library='httplib', url=connection.host) \
            as tracer:
        # Add the tracer obj as an attr to the connection obj. The tracer will
        # be used by the subsequent calls to the connection obj to add NR
        # Headers.

        connection._nr_external_tracer = tracer
        return wrapped(*args, **kwargs)

def httplib_endheaders_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    connection = instance

    # Check if _nr_skip_headers attr is present in connection obj. This attr is
    # set by the putheader_wrapper if the NR headers are already present to
    # avoid double wrapping. A double wrapping can happen if a higher level
    # library (such as requests) uses httplib underneath.

    if getattr(connection, '_nr_skip_headers', None):
        return wrapped(*args, **kwargs)

    outgoing_headers = ExternalTrace.generate_request_headers(transaction)
    for header_name, header_value in outgoing_headers:
        connection.putheader(header_name, header_value)

    return wrapped(*args, **kwargs)

def httplib_getresponse_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    response = wrapped(*args, **kwargs)

    connection = instance

    if hasattr(connection, '_nr_external_tracer'):
        tracer = connection._nr_external_tracer
        tracer.process_response_headers(response.getheaders())

    return response

def httplib_putheader_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def nr_header(header, *args, **kwargs):
        h = header.upper()
        if (h == 'X-NEWRELIC-ID') or (h == 'X-NEWRELIC-TRANSACTION'):
            return True
        return False

    connection = instance

    if nr_header(*args, **kwargs):
        connection._nr_skip_headers = True

    return wrapped(*args, **kwargs)


def instrument_httplib_connect(module):

    module.HTTPConnection.connect = ObjectWrapper(
            module.HTTPConnection.connect,
            None,
            httplib_connect_wrapper
            )

#    def url_connect_http(connection):
#        return 'http://%s/' % connection.host
#
#    newrelic.api.external_trace.wrap_external_trace(
#           module, 'HTTPConnection.connect', 'httplib',
#           url_connect_http)
#
#    def url_connect_https(connection):
#        return 'https://%s/' % connection.host
#
#    if hasattr(module, 'HTTPSConnection'):
#        newrelic.api.external_trace.wrap_external_trace(
#               module, 'HTTPSConnection.connect', 'httplib',
#               url_connect_https)

def instrument_httplib_endheaders(module):
    module.HTTPConnection.endheaders = ObjectWrapper(
            module.HTTPConnection.endheaders,
            None,
            httplib_endheaders_wrapper
            )

def instrument_httplib_getresponse(module):
    module.HTTPConnection.getresponse = ObjectWrapper(
            module.HTTPConnection.getresponse,
            None,
            httplib_getresponse_wrapper
            )

def instrument_httplib_putheader(module):
    module.HTTPConnection.putheader = ObjectWrapper(
            module.HTTPConnection.putheader,
            None,
            httplib_putheader_wrapper
            )
