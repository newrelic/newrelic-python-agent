from tornado.httpclient import HTTPRequest

from newrelic.agent import ExternalTrace, wrap_function_wrapper
from .util import retrieve_current_transaction


def _extract_url(*args, **kwargs):

    def _extract_request(request, *args, **kwargs):
        return request

    request = _extract_request(*args, **kwargs)

    # request is either a string or a HTTPRequest object
    if isinstance(request, HTTPRequest):
        url = request.url
    else:
        url = request

    return url


def _nr_wrapper_httpclient_HTTPClient_fetch_(wrapped, instance, args, kwargs):

    transaction = retrieve_current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    url = _extract_url(*args, **kwargs)

    with ExternalTrace(transaction, 'tornado.httpclient', url):
        return wrapped(*args, **kwargs)


def _nr_wrapper_httpclient_AsyncHTTPClient_fetch_(
        wrapped, instance, args, kwargs):

    transaction = retrieve_current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    url = _extract_url(*args, **kwargs)

    trace = ExternalTrace(transaction, 'tornado.httpclient', url)

    def external_trace_done(future):
        exc_info = future.exc_info()
        if exc_info:
            trace.__exit__(*exc_info)
        else:
            trace.__exit__(None, None, None)
        transaction._ref_count -= 1

    transaction._ref_count += 1
    trace.__enter__()
    future = wrapped(*args, **kwargs)
    future.add_done_callback(external_trace_done)
    return future


def instrument_tornado_httpclient(module):
    wrap_function_wrapper(module, 'HTTPClient.fetch',
            _nr_wrapper_httpclient_HTTPClient_fetch_)
    wrap_function_wrapper(module, 'AsyncHTTPClient.fetch',
            _nr_wrapper_httpclient_AsyncHTTPClient_fetch_)
