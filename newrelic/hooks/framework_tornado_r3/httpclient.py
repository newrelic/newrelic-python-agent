from tornado.httpclient import HTTPRequest

from newrelic.agent import (ExternalTrace, FunctionTrace, function_wrapper,
        wrap_function_wrapper, callable_name)
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

def _nr_wrapper_httpclient_AsyncHTTPClient_fetch_(
        wrapped, instance, args, kwargs):

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

    # For some reason if callback is not passed in to fetch, we don't see its
    # default value, None, in args or kwargs. We extract it now.
    if len(args) > 1:
        callback = args[1]
    elif 'callback' in kwargs:
        callback = kwargs['callback']
    else:
        callback = None

    if callback is not None:
        # We want to time the response handler and change its name to associate
        # it with the url.
        @function_wrapper
        def _wrap_callback(wrapped, instance, args, kwargs):
            name = callable_name(wrapped)
            name = "%s [%s]" % (name, url)
            with FunctionTrace(transaction, name=name):
                return wrapped(*args, **kwargs)

        wrapped_callback = _wrap_callback(callback)

        # We want to replace the callback with our wrapped_callback. It was
        # either passed in as a positional argument at index 1 or as a keyword
        # argument using 'callback'.
        if len(args) > 1:
            args = list(args)
            args[1] = wrapped_callback
        else:
            kwargs['callback'] = wrapped_callback

    with ExternalTrace(transaction, 'tornado.httpclient', url):
        return wrapped(*args, **kwargs)

def instrument_tornado_httpclient(module):
    wrap_function_wrapper(module, 'HTTPClient.fetch',
            _nr_wrapper_httpclient_HTTPClient_fetch_)
    wrap_function_wrapper(module, 'AsyncHTTPClient.fetch',
            _nr_wrapper_httpclient_AsyncHTTPClient_fetch_)
