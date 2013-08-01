from newrelic.agent import wrap_external_trace

def instrument(module):

    def tsocket_open_url(socket, *args, **kwargs):
        if socket.port:
            url = 'http://%s:%s' % (socket.host, socket.port)
        else:
            url = '%s' % (socket.host)

        return url

    wrap_external_trace(module, 'TSocket.open', 'thrift', tsocket_open_url)
