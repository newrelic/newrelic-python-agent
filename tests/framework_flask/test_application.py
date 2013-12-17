import webtest

from flask import Flask, render_template_string, render_template, abort

_test_application = None

def test_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late.

    global _test_application

    if _test_application:
        return _test_application

    application = Flask(__name__)

    @application.route('/index')
    def index_page():
        return 'INDEX RESPONSE'

    @application.route('/error')
    def error_page():
        raise RuntimeError('RUNTIME ERROR')

    @application.route('/abort_404')
    def abort_404_page():
        abort(404)

    @application.route('/template_string')
    def template_string():
        return render_template_string('<body><p>INDEX RESPONSE</p></body>')

    @application.route('/template_not_found')
    def template_not_found():
        return render_template('not_found')

    _test_application = webtest.TestApp(application)

    return _test_application

def test_application_index():
    application = test_application()
    response = application.get('/index')
    response.mustcontain('INDEX RESPONSE')

def test_application_error():
    application = test_application()
    response = application.get('/error', status=500, expect_errors=True)

def test_application_abort_404():
    application = test_application()
    response = application.get('/abort_404', status=404)

def test_application_not_found():
    application = test_application()
    response = application.get('/missing', status=404)

def test_application_render_template_string():
    application = test_application()
    response = application.get('/template_string')

def test_application_render_template_not_found():
    application = test_application()
    response = application.get('/template_not_found', status=500)
