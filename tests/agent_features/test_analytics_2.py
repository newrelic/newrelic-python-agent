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
        assert len(sample) == 2

        record, params = sample

        assert record['type'] == 'Transaction'
        assert record['name'] == name
        assert record['timestamp'] >= 0.0
        assert record['duration'] >= 0.0

        assert 'queueDuration' not in record
        assert 'memcacheDuration' not in record

        if capture_attributes:
            assert params['user'] == u'user-name'
            assert params['account'] == u'account-name'
            assert params['product'] == u'product-name'

            if six.PY2:
                assert params['bytes'] == u'bytes-value'
            else:
                assert 'bytes' not in params

            assert params['string'] == u'string-value'
            assert params['unicode'] == u'unicode-value'

            assert params['integer'] == 1
            assert params['float'] == 1.0

            if six.PY2:
                assert params['invalid-utf8'] == b'\xe2'
                assert params['multibyte-utf8'] == b'\xe2\x88\x9a'
            else:
                assert 'invalid-utf8' not in params
                assert 'multibyte-utf8' not in params

            assert params['multibyte-unicode'] == b'\xe2\x88\x9a'.decode('utf-8')

            assert 'list' not in params
            assert 'tuple' not in params
            assert 'dict' not in params

        else:
            assert params == {}

        if database_call_count:
            assert record['databaseDuration'] > 0
            assert record['databaseCallCount'] == database_call_count
        else:
            assert 'databaseDuration' not in record
            assert 'databaseCallCount' not in record

        if external_call_count:
            assert record['externalDuration'] > 0
            assert record['externalCallCount'] == external_call_count
        else:
            assert 'externalDuration' not in record
            assert 'externalCallCount' not in record

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

