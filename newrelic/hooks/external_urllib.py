try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import newrelic.api.external_trace
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

def instrument(module):

    if hasattr(module, 'urlretrieve'):
        wrap_function_wrapper(module, 'urlretrieve', _nr_wrapper_urlretrieve_)

    def url_opener_open(opener, url, *args, **kwargs):
        return url

    if hasattr(module, 'URLopener'):
        newrelic.api.external_trace.wrap_external_trace(
            module, 'URLopener.open', 'urllib', url_opener_open)

    def url_opener_open(opener, fullurl, *args, **kwargs):
        if isinstance(fullurl, six.string_types):
            return fullurl
        else:
            return fullurl.get_full_url()

    if hasattr(module, 'OpenerDirector'):
        newrelic.api.external_trace.wrap_external_trace(
            module, 'OpenerDirector.open', 'urllib2',
            url_opener_open)
