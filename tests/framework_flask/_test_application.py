import webtest

from flask import Flask, render_template_string, render_template, abort
from werkzeug.exceptions import NotFound

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

@application.route('/exception_404')
def exception_404_page():
    raise NotFound()

@application.route('/template_string')
def template_string():
    return render_template_string('<body><p>INDEX RESPONSE</p></body>')

@application.route('/template_not_found')
def template_not_found():
    return render_template('not_found')

@application.route('/html_insertion')
def html_insertion():
    return ('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')

_test_application = webtest.TestApp(application)
