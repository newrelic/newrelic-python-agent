import webtest

from newrelic.agent import wsgi_application, add_custom_parameter
from newrelic.core.attribute import create_intrinsic_attributes

from testing_support.fixtures import (override_application_settings,
    validate_attributes)


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'Hello World!'

    path = environ.get('PATH_INFO')
    if path == '/user_attribute':
        add_custom_parameter('test_key', 'test_value')

    response_headers = [('Content-Type', 'text/plain; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

_required_intrinsics = ['trip_id']
_forgone_intrinsics = []

@validate_attributes('intrinsic', _required_intrinsics, _forgone_intrinsics)
def test_intrinsics():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/')
    assert response.body == b'Hello World!'

_required_agent = ['request.method', 'wsgi.output.time', 'response.status']
_forgone_agent = []

@validate_attributes('agent', _required_agent, _forgone_agent)
def test_agent():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/')
    assert response.body == b'Hello World!'

_required_user = ['test_key']
_forgone_user = []

@validate_attributes('user', _required_user, _forgone_user)
def test_user():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/user_attribute')
    assert response.body == b'Hello World!'

_settings_legacy_false = {'capture_params': False}
_required_request_legacy_false = []
_forgone_request_legacy_false = ['request.parameters.foo']

@override_application_settings(_settings_legacy_false)
@validate_attributes('agent', _required_request_legacy_false,
        _forgone_request_legacy_false)
def test_capture_request_params_legacy_false():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=bar')
    assert response.body == b'Hello World!'

_settings_legacy_true = {'capture_params': True}
_required_request_legacy_true = ['request.parameters.foo']
_forgone_request_legacy_true = []

@override_application_settings(_settings_legacy_true)
@validate_attributes('agent', _required_request_legacy_true,
        _forgone_request_legacy_true)
def test_capture_request_params_legacy_true():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=bar')
    assert response.body == b'Hello World!'

_required_request_default = ['request.parameters.foo']
_forgone_request_default = []

@validate_attributes('agent', _required_request_default,
        _forgone_request_default)
def test_capture_request_params_default():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=bar')
    assert response.body == b'Hello World!'
