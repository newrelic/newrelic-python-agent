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

import pytest
import six
import webtest

from newrelic.api.wsgi_application import wsgi_application

from testing_support.fixtures import (override_application_settings,
    capture_transaction_metrics)

PAGE_CONTENTS = b'Hello World'

_browser_enabled_settings = {
    'browser_monitoring.enabled': True,
}

_browser_disabled_settings = {
    'browser_monitoring.enabled': False,
}

@wsgi_application()
def _app_list(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return [PAGE_CONTENTS]
target_application_list = webtest.TestApp(_app_list)

@wsgi_application()
def _app_iter(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    yield PAGE_CONTENTS
target_application_iter = webtest.TestApp(_app_iter)

@wsgi_application()
def _app_str(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    return PAGE_CONTENTS
target_application_str = webtest.TestApp(_app_str)

@wsgi_application()
def _app_list_exc_1(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    1/0
    return [PAGE_CONTENTS]
target_application_list_exc_1 = webtest.TestApp(_app_list_exc_1)

@wsgi_application()
def _app_list_exc_2(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    1/0
    start_response(status, response_headers)
    return [PAGE_CONTENTS]
target_application_list_exc_2 = webtest.TestApp(_app_list_exc_2)

@wsgi_application()
def _app_iter_exc_1(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    1/0
    yield PAGE_CONTENTS
target_application_iter_exc_1 = webtest.TestApp(_app_iter_exc_1)

@wsgi_application()
def _app_iter_exc_2(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    1/0
    start_response(status, response_headers)
    yield PAGE_CONTENTS
target_application_iter_exc_2 = webtest.TestApp(_app_iter_exc_2)

_target_applications = [
    target_application_list,
    target_application_iter,
    pytest.param(target_application_str, marks=pytest.mark.skipif(
                six.PY3, reason='PY3 webtest expects type(byte) '
                'so this test doesnt apply')),
    target_application_list_exc_1,
    target_application_list_exc_2,
    target_application_iter_exc_1,
    target_application_iter_exc_2,
]

@pytest.mark.parametrize('target_application', _target_applications)
def test_metrics_same_with_and_without_browser_middleware(target_application):
    with_browser_metrics = []
    without_browser_metrics = []

    @capture_transaction_metrics(with_browser_metrics)
    @override_application_settings(_browser_enabled_settings)
    def run_app_with_browser():
        try:
            resp = target_application.get('/')
        except ZeroDivisionError:
            pass
        else:
            assert resp.body == PAGE_CONTENTS

    @capture_transaction_metrics(without_browser_metrics)
    @override_application_settings(_browser_disabled_settings)
    def run_app_without_browser():
        try:
            resp = target_application.get('/')
        except ZeroDivisionError:
            pass
        else:
            assert resp.body == PAGE_CONTENTS

    run_app_with_browser()
    run_app_without_browser()

    assert with_browser_metrics == without_browser_metrics
