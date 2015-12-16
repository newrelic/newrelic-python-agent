from tornado.httpclient import HTTPRequest

from newrelic.agent import ExternalTrace, wrap_function_wrapper
from .util import retrieve_current_transaction

def _nr_wrapper_httpclient_HTTPClient_fetch_(wrapped, instance, args, kwargs):

    transaction = retrieve_current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _extract_request(request, *args, **kwargs):
        return request

    request = _extract_request(*args, **kwargs)

    # request is either a string or a HTTPRequest object
    if isinstance(request, HTTPRequest):
        url = request.url
    else:
        url = request

    with ExternalTrace(transaction, 'tornado.httpclient', url):
        return wrapped(*args, **kwargs)

def instrument_tornado_httpclient(module):
    wrap_function_wrapper(module, 'HTTPClient.fetch',
            _nr_wrapper_httpclient_HTTPClient_fetch_)
