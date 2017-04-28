from tornado.httpclient import HTTPRequest

from newrelic.agent import ExternalTrace, wrap_function_wrapper
from .util import retrieve_current_transaction


def _prepare_request(*args, **kwargs):

    def _extract_request(request, *_args, **_kwargs):
        return request, _args, _kwargs

    request, _args, _kwargs = _extract_request(*args, **kwargs)

    # request is either a string or a HTTPRequest object
    if not isinstance(request, HTTPRequest):
        url = request
        request = HTTPRequest(url, *_args, **_kwargs)

    return request


def _nr_wrapper_httpclient_HTTPClient_fetch_(wrapped, instance, args, kwargs):

    transaction = retrieve_current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    req = _prepare_request(*args, **kwargs)

    # Prepare outgoing CAT headers
    outgoing_headers = ExternalTrace.generate_request_headers(transaction)
    for header_name, header_value in outgoing_headers:
        req.headers.add(header_name, header_value)

    with ExternalTrace(transaction, 'tornado.httpclient', req.url) as trace:
        response = wrapped(req)
        # Process CAT response headers
        trace.process_response_headers(response.headers.get_all())
        return response


def _nr_wrapper_httpclient_AsyncHTTPClient_fetch_(
        wrapped, instance, args, kwargs):

    transaction = retrieve_current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _prepare_async_req(request, callback=None, raise_error=True, **kwargs):
        return _prepare_request(request, **kwargs), callback, raise_error

    req, _cb, _raise_error = _prepare_async_req(*args, **kwargs)

    # Prepare outgoing CAT headers
    outgoing_headers = ExternalTrace.generate_request_headers(transaction)
    for header_name, header_value in outgoing_headers:
        req.headers.add(header_name, header_value)

    trace = ExternalTrace(transaction, 'tornado.httpclient', req.url)

    def external_trace_done(future):
        exc_info = future.exc_info()
        if exc_info:
            trace.__exit__(*exc_info)
        else:
            response = future.result()
            # Process CAT response headers
            trace.process_response_headers(response.headers.get_all())
            trace.__exit__(None, None, None)
        transaction._ref_count -= 1

    transaction._ref_count += 1
    trace.__enter__()

    future = wrapped(req, _cb, _raise_error)
    future.add_done_callback(external_trace_done)
    return future


def instrument_tornado_httpclient(module):
    wrap_function_wrapper(module, 'HTTPClient.fetch',
            _nr_wrapper_httpclient_HTTPClient_fetch_)
    wrap_function_wrapper(module, 'AsyncHTTPClient.fetch',
            _nr_wrapper_httpclient_AsyncHTTPClient_fetch_)
