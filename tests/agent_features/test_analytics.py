import webtest
import json

from newrelic.packages import six

from testing_support.fixtures import override_application_settings

from newrelic.agent import (add_user_attribute, add_custom_parameter,
    get_browser_timing_header, get_browser_timing_footer,
    application_settings, wsgi_application, transient_function_wrapper)

from newrelic.common.encoding_utils import deobfuscate

@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'

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

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

target_application = webtest.TestApp(target_wsgi_application)

def validate_analytics_sample_data(name, capture_attributes=True):
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
        assert 'externalDuration' not in record
        assert 'databaseDuration' not in record
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

        return wrapped(*args, **kwargs)

    return _validate_analytics_sample_data

_test_capture_attributes_enabled_settings = {
    'browser_monitoring.capture_attributes': True }

@validate_analytics_sample_data(name='WebTransaction/Uri/')
@override_application_settings(_test_capture_attributes_enabled_settings)
def test_capture_attributes_enabled():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate the various fields of the footer related to analytics.
    # The fields are held by a JSON dictionary.

    data = json.loads(footer.split('NREUM.info=')[1])

    obfuscation_key = settings.license_key[:13]

    attributes = json.loads(deobfuscate(data['userAttributes'], 
            obfuscation_key))

    assert attributes['user'] == u'user-name'
    assert attributes['account'] == u'account-name'
    assert attributes['product'] == u'product-name'

    if six.PY2:
        assert attributes['bytes'] == u'bytes-value'
    else:
        assert 'bytes' not in attributes

    assert attributes['string'] == u'string-value'
    assert attributes['unicode'] == u'unicode-value'

    assert attributes['integer'] == 1
    assert attributes['float'] == 1.0

    if six.PY2:
        assert attributes['invalid-utf8'] == b'\xe2'.decode('latin-1')
        assert attributes['multibyte-utf8'] == b'\xe2\x88\x9a'.decode('latin-1')
    else:
        assert 'invalid-utf8' not in attributes
        assert 'multibyte-utf8' not in attributes

    assert attributes['multibyte-unicode'] == b'\xe2\x88\x9a'.decode('utf-8')

_test_no_attributes_recorded_settings = {
    'browser_monitoring.capture_attributes': True }

@validate_analytics_sample_data(name='WebTransaction/Uri/',
        capture_attributes=False)
@override_application_settings(_test_no_attributes_recorded_settings)
def test_no_attributes_recorded():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/', extra_environ={
            'record_attributes': 'FALSE'})

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate the various fields of the footer related to analytics.
    # The fields are held by a JSON dictionary.

    data = json.loads(footer.split('NREUM.info=')[1])

    # As we are not recording any user attributes, we should not
    # actually have an entry at all in the footer.

    assert 'userAttributes' not in data 

_test_analytic_events_capture_attributes_disabled_settings = {
    'analytics_events.capture_attributes': False,
    'browser_monitoring.capture_attributes': True }

@validate_analytics_sample_data(name='WebTransaction/Uri/',
        capture_attributes=False)
@override_application_settings(
        _test_analytic_events_capture_attributes_disabled_settings)
def test_analytic_events_capture_attributes_disabled():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert settings.analytics_events.enabled
    assert settings.analytics_events.transactions.enabled
    assert not settings.analytics_events.capture_attributes

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that userAttributes is not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'userAttributes' in data

@validate_analytics_sample_data(name='WebTransaction/Uri/')
def test_capture_attributes_default():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert not settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that userAttributes is not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'userAttributes' not in data

_test_analytic_events_background_task_settings = {
    'browser_monitoring.capture_attributes': True }

@validate_analytics_sample_data(name='OtherTransaction/Uri/')
@override_application_settings(
        _test_analytic_events_background_task_settings)
def test_analytic_events_background_task():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert settings.analytics_events.enabled
    assert settings.analytics_events.transactions.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/', extra_environ={
            'newrelic.set_background_task': True})

    assert response.html.html.head.script is None

_test_capture_attributes_disabled_settings = {
    'browser_monitoring.capture_attributes': False }

@validate_analytics_sample_data(name='WebTransaction/Uri/')
@override_application_settings(_test_capture_attributes_disabled_settings)
def test_capture_attributes_disabled():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert not settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that userAttributes is not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'userAttributes' not in data

@transient_function_wrapper('newrelic.core.stats_engine',
        'SampledDataSet.add')
def validate_no_analytics_sample_data(wrapped, instance, args, kwargs):
    assert False, 'Should not be recording analytic event.'
    return wrapped(*args, **kwargs)

_test_collect_analytic_events_disabled_settings = {
    'collect_analytics_events': False,
    'browser_monitoring.capture_attributes': True }

@validate_no_analytics_sample_data
@override_application_settings(_test_collect_analytic_events_disabled_settings)
def test_collect_analytic_events_disabled():
    settings = application_settings()

    assert not settings.collect_analytics_events

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that userAttributes is not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'userAttributes' in data

_test_analytic_events_disabled_settings = {
    'analytics_events.enabled': False,
    'browser_monitoring.capture_attributes': True }

@validate_no_analytics_sample_data
@override_application_settings(_test_analytic_events_disabled_settings)
def test_analytic_events_disabled():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert not settings.analytics_events.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that userAttributes is not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'userAttributes' in data

_test_analytic_events_transactions_disabled_settings = {
    'analytics_events.transactions.enabled': False,
    'browser_monitoring.capture_attributes': True }

@validate_no_analytics_sample_data
@override_application_settings(
        _test_analytic_events_transactions_disabled_settings)
def test_analytic_events_transactions_disabled():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert settings.analytics_events.enabled
    assert not settings.analytics_events.transactions.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.capture_attributes

    assert settings.js_agent_loader

    response = target_application.get('/')

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that userAttributes is not present, since should
    # be disabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'userAttributes' in data
