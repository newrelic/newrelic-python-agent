import newrelic.api.external_trace

def instrument(module):

    def url_request(request, method, url, *args, **kwargs):
        return url

    newrelic.api.external_trace.wrap_external_trace(
        module, 'RequestMethods.request_encode_url', 'urllib3',
        url_request)

    newrelic.api.external_trace.wrap_external_trace(
        module, 'RequestMethods.request_encode_body', 'urllib3',
        url_request)
