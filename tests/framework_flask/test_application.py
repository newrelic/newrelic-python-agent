import webtest

from flask import Flask, render_template_string, render_template, abort

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

test_application = webtest.TestApp(application)

def test_application_index():
    response = test_application.get('/index')
    response.mustcontain('INDEX RESPONSE')

def test_application_error():
    response = test_application.get('/error', status=500, expect_errors=True)

def test_application_abort_404():
    response = test_application.get('/abort_404', status=404)

def test_application_not_found():
    response = test_application.get('/missing', status=404)

def test_application_render_template_string():
    response = test_application.get('/template_string')

def test_application_render_template_not_found():
    response = test_application.get('/template_not_found', status=500)
