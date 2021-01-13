# -*- coding: utf-8 -*-
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

import gc
import webtest
import pytest
import time
from newrelic.api.application import application_instance
from newrelic.api.web_transaction import WebTransaction
from testing_support.fixtures import (validate_transaction_metrics,
        validate_attributes)
from testing_support.sample_applications import simple_app
import newrelic.packages.six as six
application = webtest.TestApp(simple_app)


# TODO: WSGI metrics must not be generated for a WebTransaction
METRICS = (
    ('Python/WSGI/Input/Bytes', None),
    ('Python/WSGI/Input/Time', None),
    ('Python/WSGI/Input/Calls/read', None),
    ('Python/WSGI/Input/Calls/readline', None),
    ('Python/WSGI/Input/Calls/readlines', None),
    ('Python/WSGI/Output/Bytes', None),
    ('Python/WSGI/Output/Time', None),
    ('Python/WSGI/Output/Calls/yield', None),
    ('Python/WSGI/Output/Calls/write', None),
)


# TODO: Add rollup_metrics=METRICS
@validate_transaction_metrics(
        'test_base_web_transaction',
        group='Test')
@validate_attributes('agent',
[
    'request.headers.accept', 'request.headers.contentLength',
    'request.headers.contentType', 'request.headers.host',
    'request.headers.referer', 'request.headers.userAgent', 'request.method',
    'request.uri', 'response.status', 'response.headers.contentLength',
    'response.headers.contentType', 'request.parameters.foo',
    'request.parameters.boo', 'webfrontend.queue.seconds',
])
@pytest.mark.parametrize('use_bytes', (True, False))
def test_base_web_transaction(use_bytes):
    application = application_instance()

    request_headers = {
        'Accept': 'text/plain',
        'Content-Length': '0',
        'Content-Type': 'text/plain',
        'Host': 'localhost',
        'Referer': 'http://example.com?q=1&boat=⛵',
        'User-Agent': 'potato',
        'X-Request-Start': str(time.time() - 0.2),
        'newRelic': 'invalid',
    }

    if use_bytes:
        byte_headers = {}

        for name, value in request_headers.items():
            name = name.encode('utf-8')
            try:
                value = value.encode('utf-8')
            except UnicodeDecodeError:
                assert six.PY2
            byte_headers[name] = value

        request_headers = byte_headers

    transaction = WebTransaction(
            application,
            'test_base_web_transaction',
            group='Test',
            scheme='http',
            host='localhost',
            port=8000,
            request_method='HEAD',
            request_path='/foobar',
            query_string='foo=bar&boo=baz',
            headers=request_headers.items(),
    )

    if use_bytes:
        response_headers = ((b'Content-Length', b'0'),
                            (b'Content-Type', b'text/plain'))
    else:
        response_headers = (('Content-Length', '0'),
                            ('Content-Type', 'text/plain'))

    with transaction:
        transaction.process_response(200, response_headers)


@pytest.fixture()
def validate_no_garbage():
    yield

    # garbage collect until everything is reachable
    while gc.collect():
        pass

    assert not gc.garbage


@validate_transaction_metrics(
    name='',
    group='Uri',
)
def test_wsgi_app_memory(validate_no_garbage):
    application.get('/')
