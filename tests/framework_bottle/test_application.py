import webtest

from bottle import route, default_app

@route('/index')
def index():
    return 'INDEX RESPONSE'

application = application = default_app()
test_application = webtest.TestApp(application)

def test_application_index():
    response = test_application.get('/index')
    response.mustcontain('INDEX RESPONSE')
