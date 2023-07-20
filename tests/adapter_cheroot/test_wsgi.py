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

import cheroot.wsgi
import newrelic.api.transaction
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wsgi_test_app(environ, start_response):
    newrelic.api.transaction.set_transaction_name('wsgi_test_transaction')
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return [b'Hello world!']


def start_response(status, response_headers, exc_info=None):
    """Empty callable"""
    pass


_test_scoped_metrics = [
    ('Python/WSGI/Finalize', 1),
    ('Python/WSGI/Application', 1),
    ('Function/test_wsgi:wsgi_test_app', 1),
]


@validate_transaction_metrics('wsgi_test_transaction',
        scoped_metrics=_test_scoped_metrics)
def test_wsgi_test_function_transaction_metrics_positional_args():
    server = cheroot.wsgi.Server(('127.0.0.1', get_open_port()), wsgi_test_app)
    environ = {'REQUEST_URI': '/'}
    resp = server.wsgi_app(environ, start_response)

    if hasattr(resp, 'close'):
        resp.close()


@validate_transaction_metrics('wsgi_test_transaction',
        scoped_metrics=_test_scoped_metrics)
def test_wsgi_test_function_transaction_metrics_keyword_args():
    server = cheroot.wsgi.Server(bind_addr=('127.0.0.1', get_open_port()),
                                 wsgi_app=wsgi_test_app)
    environ = {'REQUEST_URI': '/'}
    resp = server.wsgi_app(environ, start_response)

    if hasattr(resp, 'close'):
        resp.close()
