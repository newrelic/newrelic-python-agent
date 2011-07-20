from newrelic.agent import wrap_external_trace

def instrument(module):

    def url_urlretrieve(url, *args, **kwargs):
        return url

    wrap_external_trace(module, 'urlretrieve', 'urllib', url_urlretrieve)
