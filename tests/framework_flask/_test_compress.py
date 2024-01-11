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

try:
    from io import BytesIO as IO
except ImportError:
    import StringIO as IO

import webtest

from flask import Flask
from flask import Response
from flask import send_file
from flask_compress import Compress

from newrelic.api.transaction import (get_browser_timing_header,
        get_browser_timing_footer)

application = Flask(__name__)

compress = Compress()
compress.init_app(application)


@application.route('/compress')
def index_page():
    return '<body>' + 500 * 'X' + '</body>'


@application.route('/html_insertion')
def html_insertion():
    return ('<!DOCTYPE html><html><head>Some header</head>'
           '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
           '</body></html>')


@application.route('/html_insertion_manual')
def html_insertion_manual():
    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    assert header == ''
    assert footer == ''

    return ('<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')


@application.route('/html_insertion_unnamed_attachment_header')
def html_insertion_unnamed_attachment_header():
    response = Response(
            response='<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')
    response.headers.add('Content-Disposition',
                'attachment')
    return response


@application.route('/html_insertion_named_attachment_header')
def html_insertion_named_attachment_header():
    response = Response(
            response='<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>')
    response.headers.add('Content-Disposition',
                'attachment; filename="X"')
    return response


@application.route('/html_served_from_file')
def html_served_from_file():
    file = IO()
    contents = b"""
    <!DOCTYPE html><html><head>Some header</head>
    <body><h1>My First Heading</h1><p>My first paragraph.</p>
    </body></html>
    """
    file.write(contents)
    file.seek(0)
    return send_file(file, mimetype='text/html')


@application.route('/text_served_from_file')
def text_served_from_file():
    file = IO()
    contents = b"""
    <!DOCTYPE html><html><head>Some header</head>
    <body><h1>My First Heading</h1><p>My first paragraph.</p>
    </body></html>
    """
    file.write(contents)
    file.seek(0)
    return send_file(file, mimetype='text/plain')


_test_application = webtest.TestApp(application)


@application.route('/empty_content_type')
def empty_content_type():
    response = Response(
            response='<!DOCTYPE html><html><head>Some header</head>'
            '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
            '</body></html>', mimetype='')
    assert response.mimetype is None
    return response
