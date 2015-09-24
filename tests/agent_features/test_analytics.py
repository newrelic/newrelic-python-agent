import webtest
import json

try:
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

import sqlite3 as db

from newrelic.packages import six

from testing_support.fixtures import (override_application_settings,
        validate_analytics_sample_data)

from newrelic.agent import (add_user_attribute, add_custom_parameter,
        get_browser_timing_header, get_browser_timing_footer,
        application_settings, wsgi_application, transient_function_wrapper)

from newrelic.common.encoding_utils import deobfuscate

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

#====================== Test cases ====================================

_test_capture_attributes_enabled_settings = {
    'browser_monitoring.attributes.enabled': True }

@validate_analytics_sample_data(name='WebTransaction/Uri/')
@override_application_settings(_test_capture_attributes_enabled_settings)
def test_capture_attributes_enabled():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate the various fields of the footer related to analytics.
    # The fields are held by a JSON dictionary.

    data = json.loads(footer.split('NREUM.info=')[1])

    obfuscation_key = settings.license_key[:13]

    attributes = json.loads(deobfuscate(data['atts'],
            obfuscation_key))
    user_attrs = attributes['u']

    assert user_attrs['user'] == u'user-name'
    assert user_attrs['account'] == u'account-name'
    assert user_attrs['product'] == u'product-name'

    if six.PY2:
        assert user_attrs['bytes'] == u'bytes-value'
    else:
        assert 'bytes' not in user_attrs

    assert user_attrs['string'] == u'string-value'
    assert user_attrs['unicode'] == u'unicode-value'

    assert user_attrs['integer'] == 1
    assert user_attrs['float'] == 1.0

    if six.PY2:
        assert user_attrs['invalid-utf8'] == b'\xe2'.decode('latin-1')
        assert user_attrs['multibyte-utf8'] == b'\xe2\x88\x9a'.decode('latin-1')
    else:
        assert 'invalid-utf8' not in user_attrs
        assert 'multibyte-utf8' not in user_attrs

    assert user_attrs['multibyte-unicode'] == b'\xe2\x88\x9a'.decode('utf-8')

_test_no_attributes_recorded_settings = {
    'browser_monitoring.attributes.enabled': True }

@validate_analytics_sample_data(name='WebTransaction/Uri/',
        capture_attributes=False)
@override_application_settings(_test_no_attributes_recorded_settings)
def test_no_attributes_recorded():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/', extra_environ={
            'record_attributes': 'FALSE'})

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate the various fields of the footer related to analytics.
    # The fields are held by a JSON dictionary.

    data = json.loads(footer.split('NREUM.info=')[1])

    # As we are not recording any user or agent attributes, we should not
    # actually have an entry at all in the footer.

    assert 'atts' not in data

_test_analytic_events_capture_attributes_disabled_settings = {
    'transaction_events.attributes.enabled': False,
    'browser_monitoring.attributes.enabled': True }

@validate_analytics_sample_data(name='WebTransaction/Uri/',
        capture_attributes=False)
@override_application_settings(
        _test_analytic_events_capture_attributes_disabled_settings)
def test_analytic_events_capture_attributes_disabled():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert settings.transaction_events.enabled
    assert not settings.transaction_events.attributes.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that attributes are present, since browser monitoring should
    # be enabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'atts' in data

@validate_analytics_sample_data(name='WebTransaction/Uri/')
def test_capture_attributes_default():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert not settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that attributes are not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'atts' not in data

_test_analytic_events_background_task_settings = {
    'browser_monitoring.attributes.enabled': True }

@validate_analytics_sample_data(name='OtherTransaction/Uri/')
@override_application_settings(
        _test_analytic_events_background_task_settings)
def test_analytic_events_background_task():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert settings.transaction_events.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/', extra_environ={
            'newrelic.set_background_task': True})

    assert response.html.html.head.script is None

_test_capture_attributes_disabled_settings = {
    'browser_monitoring.attributes.enabled': False }

@validate_analytics_sample_data(name='WebTransaction/Uri/')
@override_application_settings(_test_capture_attributes_disabled_settings)
def test_capture_attributes_disabled():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert not settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that attributes are not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'atts' not in data

@transient_function_wrapper('newrelic.core.stats_engine',
        'SampledDataSet.add')
def validate_no_analytics_sample_data(wrapped, instance, args, kwargs):
    assert False, 'Should not be recording analytic event.'
    return wrapped(*args, **kwargs)

_test_collect_analytic_events_disabled_settings = {
    'collect_analytics_events': False,
    'browser_monitoring.attributes.enabled': True }

@validate_no_analytics_sample_data
@override_application_settings(_test_collect_analytic_events_disabled_settings)
def test_collect_analytic_events_disabled():
    settings = application_settings()

    assert not settings.collect_analytics_events

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that attributes are present, since should
    # be enabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'atts' in data

_test_analytic_events_disabled_settings = {
    'transaction_events.enabled': False,
    'browser_monitoring.attributes.enabled': True }

@validate_no_analytics_sample_data
@override_application_settings(_test_analytic_events_disabled_settings)
def test_analytic_events_disabled():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert not settings.transaction_events.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that attributes are present, since should
    # be enabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'atts' in data

# -------------- Test call counts in analytic events ----------------

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

    # Validate actual body content as sanity check.

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

    # Validate actual body content as sanity check.

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

    # Validate actual body content as sanity check.

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

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'
