import webtest

try:
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

import sqlite3 as db

from newrelic.packages import six

from newrelic.agent import (add_user_attribute, add_custom_parameter,
    get_browser_timing_header, get_browser_timing_footer,
    application_settings, wsgi_application, transient_function_wrapper)

DATABASE_NAME = ':memory:'

@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'

    path = environ.get('PATH_INFO')

    if environ.get('record_attributes', 'TRUE') == 'TRUE':
        # The add_user_attribute() call is now just an alias for
        # calling add_custom_parameter() but for backward compatibility
        # still need to check it works.

        add_user_attribute('user', 'user-name')
        add_user_attribute('account', 'account-name')
        add_user_attribute('product', 'product-name')

        add_custom_parameter('bytes', b'bytes-value')
        add_custom_parameter('string', 'string-value')
        add_custom_parameter('unicode', u'unicode-value')

        add_custom_parameter('integer', 1)
        add_custom_parameter('float', 1.0)

        add_custom_parameter('invalid-utf8', b'\xe2')
        add_custom_parameter('multibyte-utf8', b'\xe2\x88\x9a')
        add_custom_parameter('multibyte-unicode',
                b'\xe2\x88\x9a'.decode('utf-8'))

        add_custom_parameter('list', [])
        add_custom_parameter('tuple', ())
        add_custom_parameter('dict', {})

    if path == '/db' or path == '/dbext':
        connection = db.connect(DATABASE_NAME)
        connection.execute("""create table test_db (a, b, c)""")

    if path == '/ext' or path == '/dbext':
        r = urlopen('http://www.google.com')
        r.read(10)
        r = urlopen('http://www.python.org')
        r.read(10)

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

target_application = webtest.TestApp(target_wsgi_application)

def validate_analytics_sample_data(name, capture_attributes=True,
        database_call_count=0, external_call_count=0):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'SampledDataSet.add')
    def _validate_analytics_sample_data(wrapped, instance, args, kwargs):
        def _bind_params(sample, *args, **kwargs):
            return sample

        sample = _bind_params(*args, **kwargs)

        assert isinstance(sample, list)
        assert len(sample) == 3

        intrinsics, user_attributes, agent_attributes = sample
        # record, params = sample

        assert intrinsics['type'] == 'Transaction'
        assert intrinsics['name'] == name
        assert intrinsics['timestamp'] >= 0.0
        assert intrinsics['duration'] >= 0.0

        assert 'queueDuration' not in intrinsics
        assert 'memcacheDuration' not in intrinsics

        if capture_attributes:
            assert user_attributes['user'] == u'user-name'
            assert user_attributes['account'] == u'account-name'
            assert user_attributes['product'] == u'product-name'

            if six.PY2:
                assert user_attributes['bytes'] == u'bytes-value'
            else:
                assert 'bytes' not in user_attributes

            assert user_attributes['string'] == u'string-value'
            assert user_attributes['unicode'] == u'unicode-value'

            assert user_attributes['integer'] == 1
            assert user_attributes['float'] == 1.0

            if six.PY2:
                assert user_attributes['invalid-utf8'] == b'\xe2'
                assert user_attributes['multibyte-utf8'] == b'\xe2\x88\x9a'
            else:
                assert 'invalid-utf8' not in user_attributes
                assert 'multibyte-utf8' not in user_attributes

            assert user_attributes['multibyte-unicode'] == b'\xe2\x88\x9a'.decode('utf-8')

            assert 'list' not in user_attributes
            assert 'tuple' not in user_attributes
            assert 'dict' not in user_attributes

        else:
            assert user_attributes == {}

        if database_call_count:
            assert intrinsics['databaseDuration'] > 0
            assert intrinsics['databaseCallCount'] == database_call_count
        else:
            assert 'databaseDuration' not in intrinsics
            assert 'databaseCallCount' not in intrinsics

        if external_call_count:
            assert intrinsics['externalDuration'] > 0
            assert intrinsics['externalCallCount'] == external_call_count
        else:
            assert 'externalDuration' not in intrinsics
            assert 'externalCallCount' not in intrinsics

        return wrapped(*args, **kwargs)

    return _validate_analytics_sample_data

@validate_analytics_sample_data(name='WebTransaction/Uri/')
def test_no_database_or_external_attributes_in_analytics():
    """Make no external calls or database calls in the transaction and check
    if the analytic event doesn't have the databaseCallCount, databaseDuration,
    externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    response = target_application.get('/')

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

@validate_analytics_sample_data(name='WebTransaction/Uri/db',
        database_call_count=2)
def test_database_attributes_in_analytics():
    """Make database calls in the transaction and check if the analytic
    event has the databaseCallCount and databaseDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    response = target_application.get('/db')

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

@validate_analytics_sample_data(name='WebTransaction/Uri/ext',
        external_call_count=2)
def test_external_attributes_in_analytics():
    """Make external calls in the transaction and check if the analytic
    event has the externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    response = target_application.get('/ext')

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

@validate_analytics_sample_data(name='WebTransaction/Uri/dbext',
        database_call_count=2, external_call_count=2)
def test_database_and_external_attributes_in_analytics():
    """Make external calls and database calls in the transaction and check if
    the analytic event has the databaseCallCount, databaseDuration,
    externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    response = target_application.get('/dbext')

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

