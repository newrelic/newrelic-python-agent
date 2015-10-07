import sys
import json

from newrelic.agent import (application_settings, transient_function_wrapper,
        record_exception, application, callable_name)

from newrelic.common.encoding_utils import deobfuscate

from testing_support.fixtures import (override_application_settings,
        validate_transaction_event_sample_data, validate_error_event_sample_data,
        validate_non_transaction_error_event)
from testing_support.test_applications import (target_application,
            user_attributes_added)

ERR_MESSAGE = 'Transaction had bad value'
ERROR = ValueError(ERR_MESSAGE)

_user_attributes = user_attributes_added()

_error_intrinsics = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/'
}

#====================== Test cases ====================================

_test_capture_attributes_enabled_settings = {
    'browser_monitoring.attributes.enabled': True }

@validate_transaction_event_sample_data(name='WebTransaction/Uri/', capture_attributes=_user_attributes)
@validate_error_event_sample_data(required_attrs=_error_intrinsics, capture_attributes=_user_attributes)
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

    # When you round-trip through json encoding and json decoding, you
    # always end up with unicode (unicode in Python 2, str in Python 3.)
    #
    # Previously, we would drop attribute values of type 'bytes' in Python 3.
    # Now, we accept them and `json_encode` uses an encoding of 'latin-1',
    # just like it does for Python 2.

    assert user_attrs['bytes'] == u'bytes-value'
    assert user_attrs['string'] == u'string-value'
    assert user_attrs['unicode'] == u'unicode-value'

    assert user_attrs['invalid-utf8'] == b'\xe2'.decode('latin-1')
    assert user_attrs['multibyte-utf8'] == b'\xe2\x88\x9a'.decode('latin-1')
    assert user_attrs['multibyte-unicode'] == b'\xe2\x88\x9a'.decode('utf-8')

    assert user_attrs['integer'] == 1
    assert user_attrs['float'] == 1.0

_test_no_attributes_recorded_settings = {
    'browser_monitoring.attributes.enabled': True }

@validate_transaction_event_sample_data(name='WebTransaction/Uri/',
        capture_attributes={})
@validate_error_event_sample_data(required_attrs=_error_intrinsics,
        capture_attributes={})
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

@validate_transaction_event_sample_data(name='WebTransaction/Uri/',
        capture_attributes={})
@validate_error_event_sample_data(required_attrs=_error_intrinsics,
        capture_attributes={})
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

@validate_transaction_event_sample_data(name='WebTransaction/Uri/', capture_attributes=_user_attributes)
@validate_error_event_sample_data(required_attrs=_error_intrinsics, capture_attributes=_user_attributes)
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

_error_intrinsics = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'OtherTransaction/Uri/'
}

@validate_transaction_event_sample_data(name='OtherTransaction/Uri/',
        capture_attributes=_user_attributes)
@validate_error_event_sample_data(required_attrs=_error_intrinsics,
        capture_attributes=_user_attributes)
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

_error_intrinsics = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/'
}

@validate_transaction_event_sample_data(name='WebTransaction/Uri/', capture_attributes=_user_attributes)
@validate_error_event_sample_data(required_attrs=_error_intrinsics, capture_attributes=_user_attributes)
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
@validate_error_event_sample_data(required_attrs=_error_intrinsics, capture_attributes=_user_attributes)
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
@validate_error_event_sample_data(required_attrs=_error_intrinsics, capture_attributes=_user_attributes)
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

# FIXME -- test for no error events once configuration merged in

# -------------- Test call counts in analytic events ----------------

@validate_transaction_event_sample_data(name='WebTransaction/Uri/', capture_attributes=_user_attributes)
@validate_error_event_sample_data(required_attrs=_error_intrinsics, capture_attributes=_user_attributes)
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

_error_intrinsics = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/db'
}

@validate_transaction_event_sample_data(name='WebTransaction/Uri/db',
        capture_attributes=_user_attributes, database_call_count=2)
@validate_error_event_sample_data(required_attrs=_error_intrinsics,
        capture_attributes=_user_attributes, database_call_count=2)
def test_database_attributes_in_analytics():
    """Make database calls in the transaction and check if the analytic
    event has the databaseCallCount and databaseDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    test_environ = {
                'db' : '2',
    }
    response = target_application.get('/db', extra_environ=test_environ)

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

_error_intrinsics = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/ext'
}

@validate_transaction_event_sample_data(name='WebTransaction/Uri/ext',
        capture_attributes=_user_attributes, external_call_count=2)
@validate_error_event_sample_data(required_attrs=_error_intrinsics,
        capture_attributes=_user_attributes, external_call_count=2)
def test_external_attributes_in_analytics():
    """Make external calls in the transaction and check if the analytic
    event has the externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    test_environ = {
                'external' : '2',
    }
    response = target_application.get('/ext', extra_environ=test_environ)

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

_error_intrinsics = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/dbext'
}

@validate_transaction_event_sample_data(name='WebTransaction/Uri/dbext',
        capture_attributes=_user_attributes, database_call_count=2,
        external_call_count=2)
@validate_error_event_sample_data(required_attrs=_error_intrinsics,
        capture_attributes=_user_attributes, database_call_count=2,
        external_call_count=2)
def test_database_and_external_attributes_in_analytics():
    """Make external calls and database calls in the transaction and check if
    the analytic event has the databaseCallCount, databaseDuration,
    externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    test_environ = {
                'db' : '2',
                'external' : '2',
    }
    response = target_application.get('/dbext', extra_environ=test_environ)

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.text

    # Validate actual body content as sanity check.

    assert content == 'RESPONSE'

# -------------- Test Error Events outside of transaction ----------------

ERR_MESSAGE = 'Transaction had bad value'
ERROR = ValueError(ERR_MESSAGE)

_intrinsic_attributes = {
    'type': 'TransactionError',
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName': None,
}

@validate_non_transaction_error_event(_intrinsic_attributes)
def test_error_event_outside_transaction():
    try:
        raise ERROR
    except ValueError:
        app = application()
        record_exception(*sys.exc_info(), application=app)

