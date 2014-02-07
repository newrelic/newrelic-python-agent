import webtest

from newrelic.packages import six

from testing_support.fixtures import validate_transaction_errors

import cherrypy

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

application = cherrypy.Application(Application())
test_application = webtest.TestApp(application)

@validate_transaction_errors(errors=[])
def test_application_index():
    response = test_application.get('')
    response.mustcontain('INDEX RESPONSE')

@validate_transaction_errors(errors=[])
def test_application_index_agent_disabled():
    environ = { 'newrelic.enabled': False }
    response = test_application.get('', extra_environ=environ)
    response.mustcontain('INDEX RESPONSE')

@validate_transaction_errors(errors=[])
def test_application_missing():
    response = test_application.get('/missing', status=404)

if six.PY3:
    _test_application_unexpected_exception_errors = ['builtins:RuntimeError']
else:
    _test_application_unexpected_exception_errors = ['exceptions:RuntimeError']

@validate_transaction_errors(
        errors=_test_application_unexpected_exception_errors)
def test_application_unexpected_exception():
    response = test_application.get('/error', status=500)

@validate_transaction_errors(errors=[])
def test_application_not_found():
    response = test_application.get('/not_found', status=404)

@validate_transaction_errors(errors=[])
def test_application_not_found_as_http_error():
    response = test_application.get('/not_found_as_http_error', status=404)

@validate_transaction_errors(errors=[])
def test_application_internal_redirect():
    response = test_application.get('/internal_redirect')
    response.mustcontain('INDEX RESPONSE')

@validate_transaction_errors(errors=[])
def test_application_external_redirect():
    response = test_application.get('/external_redirect', status=302)

@validate_transaction_errors(errors=[])
def test_application_upload_files():
    response = test_application.post('/upload_files',
            upload_files=[('files', __file__)])

@validate_transaction_errors(errors=[])
def test_application_encode_multipart():
    content_type, body = test_application.encode_multipart(
            params=[('field', 'value')], files=[('files', __file__)])
    response = test_application.request('/encode_multipart',
            method='POST', content_type=content_type, body=body)
