import newrelic.api.external_trace
import newrelic.packages.six as six

def instrument(module):

    def url_urlretrieve(url, *args, **kwargs):
        return url

    if hasattr(module, 'urlretrieve'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'urlretrieve', 'urllib', url_urlretrieve)

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
