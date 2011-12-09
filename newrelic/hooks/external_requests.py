import newrelic.api.external_trace

def instrument(module):

    def url_request(method, url, *args, **kwargs):
        return url

    newrelic.api.external_trace.wrap_external_trace(
           module, 'request', 'requests', url_request)
