import webtest

from flask import Flask, render_template_string, render_template, abort
from werkzeug.exceptions import NotFound
from werkzeug.routing import Rule

try:
    # The __version__ attribute was only added in 0.7.0.
    from flask import __version__ as flask_version
    is_gt_flask060 = True
except ImportError:
    is_gt_flask060 = False

application = Flask(__name__)

@application.route('/index')
def index_page():
    return 'INDEX RESPONSE'

if is_gt_flask060:
    application.url_map.add(Rule('/endpoint', endpoint='endpoint'))

    @application.endpoint('endpoint')
    def endpoint_page():
        return 'ENDPOINT RESPONSE'

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
