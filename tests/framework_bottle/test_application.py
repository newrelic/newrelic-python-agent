import webtest

from bottle import route, error, default_app

@route('/index')
def index_page():
    return 'INDEX RESPONSE'

@route('/error')
def error_page():
    raise RuntimeError('RUNTIME ERROR')

@error(404)
def error404_page(error):
    return 'NOT FOUND'

application = application = default_app()
test_application = webtest.TestApp(application)

def test_application_index():
    response = test_application.get('/index')
    response.mustcontain('INDEX RESPONSE')

def test_application_error():
    response = test_application.get('/error', status=500, expect_errors=True)

def test_application_not_found():
    response = test_application.get('/missing', status=404)
    response.mustcontain('NOT FOUND')
