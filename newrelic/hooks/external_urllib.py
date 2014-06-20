try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import newrelic.packages.six as six

from newrelic.agent import (current_transaction,
    wrap_function_wrapper, ExternalTrace, FunctionTrace)

def _nr_wrapper_urlretrieve_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _bind_params(url, *args, **kwargs):
        return url

    url = _bind_params(*args, **kwargs)

    details = urlparse.urlparse(url)

    if details.hostname is None:
        with FunctionTrace(transaction, 'urllib:urlretrieve'):
            return wrapped(*args, **kwargs)

    with ExternalTrace(transaction, 'urllib', url):
        return wrapped(*args, **kwargs)

def _nr_wrapper_url_opener_open_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _bind_params(fullurl, *args, **kwargs):
        if isinstance(fullurl, six.string_types):
            return fullurl
        else:
            return fullurl.get_full_url()

    url = _bind_params(*args, **kwargs)

    details = urlparse.urlparse(url)

    if details.hostname is None:
        with FunctionTrace(transaction, 'urllib:URLopener.open'):
            return wrapped(*args, **kwargs)

    with ExternalTrace(transaction, 'urllib', url):
        return wrapped(*args, **kwargs)

def _nr_wrapper_opener_director_open_(wrapped, instance, args, kwargs):
    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    def _bind_params(fullurl, *args, **kwargs):
        if isinstance(fullurl, six.string_types):
            return fullurl
        else:
            return fullurl.get_full_url()

    url = _bind_params(*args, **kwargs)

    details = urlparse.urlparse(url)

    if details.hostname is None:
        with FunctionTrace(transaction, 'urllib2:OpenerDirector.open'):
            return wrapped(*args, **kwargs)

    with ExternalTrace(transaction, 'urllib2', url):
        return wrapped(*args, **kwargs)

def instrument(module):

    if hasattr(module, 'urlretrieve'):
        wrap_function_wrapper(module, 'urlretrieve', _nr_wrapper_urlretrieve_)

    if hasattr(module, 'URLopener'):
        wrap_function_wrapper(module, 'URLopener.open',
            _nr_wrapper_url_opener_open_)

    if hasattr(module, 'OpenerDirector'):
        wrap_function_wrapper(module, 'OpenerDirector.open',
            _nr_wrapper_opener_director_open_)
