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

import webtest

from flask import Flask, render_template_string, render_template, abort
from werkzeug.exceptions import NotFound
from werkzeug.routing import Rule

application = Flask(__name__)

@application.route('/index')
def index_page():
    return 'INDEX RESPONSE'

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
