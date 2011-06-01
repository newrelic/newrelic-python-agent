from newrelic.agent import (wrap_external_trace)

def wrap_transport_request(self, host, handler, *args, **kwargs):
    return "http://%s%s" % (host, handler)

def instrument(module):

    wrap_external_trace(module, 'Transport.request', 'xmlrpclib',
                        wrap_transport_request)
