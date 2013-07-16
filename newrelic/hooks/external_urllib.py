import newrelic.api.external_trace

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
