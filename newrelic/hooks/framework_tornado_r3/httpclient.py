from tornado.httpclient import HTTPRequest

from newrelic.agent import (ExternalTrace, FunctionTrace, function_wrapper,
        wrap_function_wrapper, callable_name)
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

    # If callback is not passed in to fetch, we don't see its default value,
    # None, in args or kwargs. If callback exists we extract it now and replace
    # it with a wrapped version to associate the url with the callback.
    @function_wrapper
    def _wrap_callback(wrapped, instance, args, kwargs):
        name = callable_name(wrapped)
        name = "%s [%s]" % (name, url)
        with FunctionTrace(transaction, name=name):
            return wrapped(*args, **kwargs)

    if len(args) > 1:
        args = list(args)
        args[1] = _wrap_callback(args[1])
    elif 'callback' in kwargs:
        kwargs['callback'] = _wrap_callback(kwargs['callback'])

    with ExternalTrace(transaction, 'tornado.httpclient', url):
        return wrapped(*args, **kwargs)

def instrument_tornado_httpclient(module):
    wrap_function_wrapper(module, 'HTTPClient.fetch',
            _nr_wrapper_httpclient_HTTPClient_fetch_)
    wrap_function_wrapper(module, 'AsyncHTTPClient.fetch',
            _nr_wrapper_httpclient_AsyncHTTPClient_fetch_)
