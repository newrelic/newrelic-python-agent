# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
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


def simple_get(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b'external response')


class MockExternalHTTPServer(threading.Thread):
    # To use this class in a test one needs to start and stop this server
    # before and after making requests to the test app that makes the external
    # calls. For an example see:
    # ../framework_tornado_r3/test_async_application.py
    RESPONSE = b'external response'

    def __init__(self, handler=simple_get, port=None, *args, **kwargs):
        super(MockExternalHTTPServer, self).__init__(*args, **kwargs)
        self.daemon = True
        handler = type('ResponseHandler',
                (BaseHTTPServer.BaseHTTPRequestHandler, object,),
                {
                    'do_GET': handler,
                    'do_OPTIONS': handler,
                    'do_HEAD': handler,
                    'do_POST': handler,
                    'do_PUT': handler,
                    'do_PATCH': handler,
                    'do_DELETE': handler,
                })

        if port:
            self.httpd = BaseHTTPServer.HTTPServer(('localhost', port), handler)
            self.port = port
        else:
            # If port not set, try to bind to a port until successful
            retries = 5  # Set retry limit to prevent infinite loops
            self.port = None  # Initialize empty
            while not self.port and retries > 0:
                retries -= 1
                try:
                    # Obtain random open port
                    port = self.get_open_port()
                    # Attempt to bind to port
                    self.httpd = BaseHTTPServer.HTTPServer(('localhost', port), handler)
                    self.port = port
                except OSError as exc:
                    # Reraise errors other than port already in use
                    if "Address already in use" not in exc:
                        raise


    @staticmethod
    def get_open_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port

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


def incoming_headers_to_body_text(self):
    response = str(self.headers).encode('utf-8')
    self.send_response(200)
    self.end_headers()
    self.wfile.write(response)


class MockExternalHTTPHResponseHeadersServer(MockExternalHTTPServer):
    """
    MockExternalHTTPHResponseHeadersServer will send the incoming
    request headers back as the response.body, allowing us to validate
    httpclient request headers.

    """

    def __init__(self, handler=incoming_headers_to_body_text, port=None):
        super(MockExternalHTTPHResponseHeadersServer, self).__init__(
                handler=handler, port=port)
