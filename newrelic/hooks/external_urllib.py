try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import newrelic.packages.six as six

from newrelic.agent import (current_transaction,
    wrap_function_wrapper, ExternalTrace, FunctionTrace)

def _nr_wrapper_factory(bind_params_fn, function_name, external_name):
    # Wrapper functions will be similar for monkeypatching the different
    # urllib functions and methods, so a factory function to create them is
    # used to reduce repetitiveness.

    # Parameters:
    #
    # bind_params_fn: Function that returns the URL.
    # function_name: String. The name to be used by FunctionTrace.
    # external_name: String. The name to be used by ExternalTrace.

    def _nr_wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        url = bind_params_fn(*args, **kwargs)

        details = urlparse.urlparse(url)

        if details.hostname is None:
            with FunctionTrace(transaction, function_name):
                return wrapped(*args, **kwargs)

        with ExternalTrace(transaction, external_name, url):
            return wrapped(*args, **kwargs)

    return _nr_wrapper

def bind_params_urlretrieve(url, *args, **kwargs):
    return url

def bind_params_open(fullurl, *args, **kwargs):

    if isinstance(fullurl, six.string_types):
        return fullurl
    else:
        return fullurl.get_full_url()

def instrument(module):

    if hasattr(module, 'urlretrieve'):

        _nr_wrapper_urlretrieve_ = _nr_wrapper_factory(
            bind_params_urlretrieve, 'urllib:urlretrieve', 'urllib')

        wrap_function_wrapper(module, 'urlretrieve', _nr_wrapper_urlretrieve_)

    if hasattr(module, 'URLopener'):

        _nr_wrapper_url_opener_open_ = _nr_wrapper_factory(
            bind_params_open, 'urllib:URLopener.open', 'urllib')

        wrap_function_wrapper(module, 'URLopener.open',
            _nr_wrapper_url_opener_open_)

    if hasattr(module, 'OpenerDirector'):

        _nr_wrapper_opener_director_open_ = _nr_wrapper_factory(
            bind_params_open, 'urllib2:OpenerDirector.open', 'urllib2')

        wrap_function_wrapper(module, 'OpenerDirector.open',
            _nr_wrapper_opener_director_open_)
