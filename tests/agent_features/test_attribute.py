import webtest

from newrelic.agent import wsgi_application
from newrelic.core.attribute import create_intrinsic_attributes

from testing_support.fixtures import (override_application_settings,
    validate_attributes)


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'Hello World!'

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

