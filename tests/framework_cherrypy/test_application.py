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
import webtest

from newrelic.packages import six

from testing_support.fixtures import (
        override_application_settings, 
        override_ignore_status_codes)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

import cherrypy

CHERRYPY_VERSION = tuple(int(v) for v in cherrypy.__version__.split('.'))


class Application(object):

    @cherrypy.expose
    def index(self):
        return 'INDEX RESPONSE'

    @cherrypy.expose
    def error(self):
        raise RuntimeError('error')

    @cherrypy.expose
    def not_found(self):
        raise cherrypy.NotFound()

    @cherrypy.expose
    def not_found_as_http_error(self):
        raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def not_found_as_str_http_error(self):
        raise cherrypy.HTTPError('404 Not Found')

    @cherrypy.expose
    def bad_http_error(self):
        # this will raise HTTPError with status code 500 because 10 is not a
        # valid status code
        raise cherrypy.HTTPError('10 Invalid status code')

    @cherrypy.expose
    def internal_redirect(self):
        raise cherrypy.InternalRedirect('/')

    @cherrypy.expose
    def external_redirect(self):
        raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    def upload_files(self, files):
        return 'UPLOAD FILES RESPONSE'

    @cherrypy.expose
    def encode_multipart(self, field, files):
        return 'ENCODE MULTIPART RESPONSE'

    @cherrypy.expose
    def html_insertion(self):
        return ('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')


application = cherrypy.Application(Application())
test_application = webtest.TestApp(application)


@validate_code_level_metrics("test_application.Application", "index")
@validate_transaction_errors(errors=[])
def test_application_index():
    response = test_application.get('')
    response.mustcontain('INDEX RESPONSE')


@validate_transaction_errors(errors=[])
def test_application_index_agent_disabled():
    environ = {'newrelic.enabled': False}
    response = test_application.get('', extra_environ=environ)
    response.mustcontain('INDEX RESPONSE')


@validate_transaction_errors(errors=[])
def test_application_missing():
    test_application.get('/missing', status=404)


if six.PY3:
    _test_application_unexpected_exception_errors = ['builtins:RuntimeError']
else:
    _test_application_unexpected_exception_errors = ['exceptions:RuntimeError']


@validate_transaction_errors(
        errors=_test_application_unexpected_exception_errors)
def test_application_unexpected_exception():
    test_application.get('/error', status=500)


@validate_transaction_errors(errors=[])
def test_application_not_found():
    test_application.get('/not_found', status=404)


@validate_transaction_errors(errors=[])
def test_application_not_found_as_http_error():
    test_application.get('/not_found_as_http_error', status=404)


@validate_transaction_errors(errors=[])
def test_application_internal_redirect():
    response = test_application.get('/internal_redirect')
    response.mustcontain('INDEX RESPONSE')


@validate_transaction_errors(errors=[])
def test_application_external_redirect():
    test_application.get('/external_redirect', status=302)


@validate_transaction_errors(errors=[])
def test_application_upload_files():
    test_application.post('/upload_files', upload_files=[('files', __file__)])


@validate_transaction_errors(errors=[])
def test_application_encode_multipart():
    content_type, body = test_application.encode_multipart(
            params=[('field', 'value')], files=[('files', __file__)])
    test_application.request('/encode_multipart', method='POST',
            content_type=content_type, body=body)


_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion():
    response = test_application.get('/html_insertion')

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')


_error_endpoints = ['/not_found_as_http_error']
if CHERRYPY_VERSION >= (3, 2):
    _error_endpoints.extend(['/not_found_as_str_http_error',
        '/bad_http_error'])


@pytest.mark.parametrize('endpoint', _error_endpoints)
@pytest.mark.parametrize('ignore_overrides,expected_errors', [
    ([], ['cherrypy._cperror:HTTPError']),
    ([404, 500], []),
])
def test_ignore_status_code(endpoint, ignore_overrides, expected_errors):

    @validate_transaction_errors(errors=expected_errors)
    @override_ignore_status_codes(ignore_overrides)
    def _test():
        test_application.get(endpoint, status=[404, 500])

    _test()


@validate_transaction_errors(errors=[])
def test_ignore_status_unexpected_param():
    response = test_application.get('/?arg=1', status=404)
    response.mustcontain(no=['INDEX RESPONSE'])
