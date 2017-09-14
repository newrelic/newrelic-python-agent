import threading

from newrelic.packages.six.moves import BaseHTTPServer

# This defines an external server test apps can make requests to (instead of
# www.google.com for example). This provides 3 features:
#
# 1) This removes dependencies on external websites.
# 2) Provides a better mechanism for making an external call in a test app than
#    simple calling another endpoint the test app makes available because this
#    server will not be instrumented meaning we don't have to sort through
#    transactions to separate the ones created in the test app and the ones
#    created by an external call.
# 3) This app runs on a separate thread meaning it won't block the test app.


class MockExternalHTTPServer(threading.Thread):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls. For an example see:
    # ../framework_tornado_r3/test_async_application.py

    RESPONSE = b'external response'

    @staticmethod
    def get_ExternalHandler(response_text, response_headers, response_code):
        class ExternalHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(response_code)
                for k, v in response_headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response_text)
        return ExternalHandler

    def __init__(self, port=8989, response_text=None, response_headers=None,
            response_code=200, *args, **kwargs):
        super(MockExternalHTTPServer, self).__init__(*args, **kwargs)
        # We hardcode the port number to 8989. This allows us to easily use the
        # port number in the expected metrics that we validate without
        # reworking the fixtures. If we are worried 8989 may be in use and we
        # want to have the OS hand us an available port we could do:
        #
        # self.httpd = BaseHTTPServer.HTTPServer(('localhost', 0),
        #         MockExternalHTTPServer.ExternalHandler)
        # self.port = self.httpd.socket.getsockname()[1]

        self.port = port

        external_handler = self.get_ExternalHandler(
                response_text or self.RESPONSE,
                response_headers or {}, response_code)
        self.httpd = BaseHTTPServer.HTTPServer(('localhost', port),
                external_handler)

        self.daemon = True

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, tb):
        self.stop()

    def run(self):
        self.httpd.serve_forever()

    def stop(self):
        # Shutdowns the httpd server.
        self.httpd.shutdown()
        # Close the socket so we can reuse it.
        self.httpd.socket.close()
        self.join()


class MockExternalHTTPHResponseHeadersServer(MockExternalHTTPServer):
    """
    MockExternalHTTPHResponseHeadersServer will send the incoming
    request headers back as the response.body, allowing us to validate
    httpclient request headers.

    """
    @staticmethod
    def get_ExternalHandler(response_text, response_headers, response_code):
        class ExternalHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                response = str(self.headers).encode('utf-8')
                self.send_response(response_code)
                self.end_headers()
                self.wfile.write(response)
        return ExternalHandler
