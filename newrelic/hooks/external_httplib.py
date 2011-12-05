import newrelic.api.external_trace

def instrument(module):

    def url_connect_http(connection):
        return 'http://%s/' % connection.host

    newrelic.api.external_trace.wrap_external_trace(
           module, 'HTTPConnection.connect', 'httplib',
           url_connect_http)

    def url_connect_https(connection):
        return 'https://%s/' % connection.host

    if hasattr(module, 'HTTPSConnection'):
        newrelic.api.external_trace.wrap_external_trace(
               module, 'HTTPSConnection.connect', 'httplib',
               url_connect_https)
