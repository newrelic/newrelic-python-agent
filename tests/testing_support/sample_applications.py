import sys

try:
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

import sqlite3 as db

from newrelic.agent import (add_user_attribute, add_custom_parameter,
        wsgi_application, record_exception, get_browser_timing_header,
        get_browser_timing_footer)

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

def user_attributes_added():
    """Expected values when the custom parameters in this file are added as user
    attributes
    """
    user_attributes = _custom_parameters.copy()
    user_attributes['list'] = '[]'
    user_attributes['tuple'] = '()'
    user_attributes['dict'] = '{}'
    return user_attributes

@wsgi_application()
def sample_wsgi_application_fully_featured(environ, start_response):
    status = '200 OK'

    path = environ.get('PATH_INFO')

    if environ.get('record_attributes', 'TRUE') == 'TRUE':

        # The add_user_attribute() call is now just an alias for
        # calling add_custom_parameter() but for backward compatibility
        # still need to check it works.

        for attr, val in _custom_parameters.items():
            if attr in ['user', 'product', 'account']:
                add_user_attribute(attr, val)
            else:
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
        try:
            raise ValueError(environ['err_message'])
        except ValueError:
            record_exception(*sys.exc_info())

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
