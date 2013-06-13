from newrelic.agent import (wrap_external_trace, ExternalTrace,
        ObjectWrapper, current_transaction)


def instrument_requests_sessions(module):

    def url_request(obj, method, url, *args, **kwargs):
        return url

    #wrap_external_trace(module, 'Session.request', 'requests', url_request)

def instrument_requests_api(module):

    def url_request(method, url, *args, **kwargs):
        return url

    wrap_external_trace(module, 'request', 'requests', url_request)

def request_send_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    parent = transaction._parent_node()

    if not parent or parent.terminal_node():
        return wrapped(*args, **kwargs)

    def _args(request, *args, **kwargs):
        return request

    request = _args(*args, **kwargs)

    #with ExternalTrace(transaction, library='requests', url=request.url):
    #    return wrapped(*args, **kwargs)
    with ExternalTrace(transaction, library='requests', url=request.url) \
            as tracer:
        try:
            # Add our own extra headers to outgoing request.

            outgoing_headers = tracer.generate_request_headers()
            request.headers.update(outgoing_headers)

            response = wrapped(*args, **kwargs)
        except:  # Naked except.
            raise
        else:
            headers = response.headers
            tracer.process_response_headers(headers.items())

        return response

def instrument_requests_models(module):
    module.Session.send = ObjectWrapper(module.Session.send, None,
            request_send_wrapper)
