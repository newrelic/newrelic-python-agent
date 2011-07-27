import newrelic.api.external_trace

def instrument(module):

    def url_urlretrieve(url, *args, **kwargs):
        return url

    newrelic.api.external_trace.wrap_external_trace(
           module, 'urlretrieve', 'urllib', url_urlretrieve)
