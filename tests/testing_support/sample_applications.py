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
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

import sqlite3 as db

from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import (add_custom_parameter,
        get_browser_timing_header, get_browser_timing_footer,
        record_custom_event)
from newrelic.api.wsgi_application import wsgi_application

_custom_parameters = {
        'user' : 'user-name',
        'account' : 'account-name',
        'product' : 'product-name',
        'bytes' : b'bytes-value',
        'string' : 'string-value',
        'unicode' : u'unicode-value',
        'integer' : 1,
        'float' : 1.0,
        'invalid-utf8' : b'\xe2',
        'multibyte-utf8' : b'\xe2\x88\x9a',
        'multibyte-unicode' : b'\xe2\x88\x9a'.decode('utf-8'),
        'list' : [],
        'tuple' : (),
        'dict' : {},
}

_err_param = {
        'err-param' : 'value'
}

def user_attributes_added():
    """Expected values when the custom parameters in this file are added as user
    attributes
    """
    user_attributes = _custom_parameters.copy()
    user_attributes['list'] = '[]'
    user_attributes['tuple'] = '()'
    user_attributes['dict'] = '{}'
    return user_attributes

def error_user_params_added():
    return _err_param.copy()

@wsgi_application()
def fully_featured_app(environ, start_response):
    status = '200 OK'

    path = environ.get('PATH_INFO')
    use_user_attrs = environ.get('record_attributes', 'TRUE') == 'TRUE'

    environ['wsgi.input'].read()
    environ['wsgi.input'].readline()
    environ['wsgi.input'].readlines()

    if use_user_attrs:

        for attr, val in _custom_parameters.items():
            add_custom_parameter(attr, val)

    if 'db' in environ and int(environ['db']) > 0:
        connection = db.connect(":memory:")
        for i in range(int(environ['db']) - 1):
            connection.execute("create table test_db%d (a, b, c)" % i)

    if 'external' in environ:
        for i in range(int(environ['external'])):
            r = urlopen('http://www.python.org')
            r.read(10)

    if 'err_message' in environ:
        n_errors = int(environ.get('n_errors', 1))
        for i in range(n_errors):
            try:

                # append number to stats engine to get unique errors, so they
                # don't immediately get filtered out.

                raise ValueError(environ['err_message'] + str(i))
            except ValueError:
                if use_user_attrs:
                    notice_error(attributes=_err_param)
                else:
                    notice_error()

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    write = start_response(status, response_headers)

    write(b'')

    return [output]

@wsgi_application()
def simple_exceptional_app(environ, start_response):

    start_response('500 :(',[])

    raise ValueError('Transaction had bad value')

@wsgi_application()
def simple_app(environ, start_response):
    status = '200 OK'

    start_response(status, response_headers=[])

    return []

@wsgi_application()
def simple_custom_event_app(environ, start_response):

    params = {'snowman': u'\u2603', 'foo': 'bar'}
    record_custom_event('SimpleAppEvent', params)

    start_response(status='200 OK', response_headers=[])
    return []
