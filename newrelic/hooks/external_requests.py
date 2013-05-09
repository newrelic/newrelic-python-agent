import newrelic.api.external_trace

def instrument_requests_sessions(module):

    def url_request(obj, method, url, *args, **kwargs):
        return url

    newrelic.api.external_trace.wrap_external_trace(
           module, 'Session.request', 'requests', url_request)

def instrument_requests_api(module):

    def url_request(method, url, *args, **kwargs):
        return url

    newrelic.api.external_trace.wrap_external_trace(
           module, 'request', 'requests', url_request)
