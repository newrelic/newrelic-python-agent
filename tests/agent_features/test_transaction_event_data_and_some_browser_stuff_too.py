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

import json
import webtest

from newrelic.api.application import application_settings
from newrelic.api.background_task import background_task

from newrelic.common.encoding_utils import deobfuscate
from newrelic.common.object_wrapper import transient_function_wrapper

from testing_support.fixtures import (override_application_settings,
        validate_transaction_event_sample_data,
        validate_transaction_event_attributes)
from testing_support.sample_applications import (fully_featured_app,
            user_attributes_added)


fully_featured_application = webtest.TestApp(fully_featured_app)
_user_attributes = user_attributes_added()

#====================== Test cases ====================================

_test_capture_attributes_enabled_settings = {
    'browser_monitoring.attributes.enabled': True }

_intrinsic_attributes = {
        'name': 'WebTransaction/Uri/',
        'port': 80,
}

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
@override_application_settings(_test_capture_attributes_enabled_settings)
def test_capture_attributes_enabled():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = fully_featured_application.get('/')

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

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


    # When you round-trip through json encoding and json decoding, you
    # always end up with unicode (unicode in Python 2, str in Python 3.)
    #
    # Previously, we would drop attribute values of type 'bytes' in Python 3.
    # Now, we accept them and `json_encode` uses an encoding of 'latin-1',
    # just like it does for Python 2. This only applies to attributes in browser
    # monitoring

    browser_attributes = _user_attributes.copy()

    browser_attributes['bytes'] = u'bytes-value'
    browser_attributes['invalid-utf8'] = _user_attributes[
                                            'invalid-utf8'].decode('latin-1')
    browser_attributes['multibyte-utf8'] = _user_attributes[
                                            'multibyte-utf8'].decode('latin-1')

    for attr, value in browser_attributes.items():
        assert user_attrs[attr] == value, (
                "attribute %r expected %r, found %r" %
                (attr, value, user_attrs[attr]))

_test_no_attributes_recorded_settings = {
    'browser_monitoring.attributes.enabled': True }

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs={})
@override_application_settings(_test_no_attributes_recorded_settings)
def test_no_attributes_recorded():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = fully_featured_application.get('/', extra_environ={
            'record_attributes': 'FALSE'})

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

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

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs={})
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

    response = fully_featured_application.get('/')

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate that attributes are present, since browser monitoring should
    # be enabled.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'atts' in data

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
def test_capture_attributes_default():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert not settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = fully_featured_application.get('/')

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

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

_intrinsic_attributes = {
        'name': 'OtherTransaction/Uri/'
}

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
@override_application_settings(
        _test_analytic_events_background_task_settings)
def test_analytic_events_background_task():
    settings = application_settings()

    assert settings.collect_analytics_events
    assert settings.transaction_events.enabled

    assert settings.browser_monitoring.enabled
    assert settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = fully_featured_application.get('/', extra_environ={
            'newrelic.set_background_task': True})

    assert response.html.html.head.script is None

_test_capture_attributes_disabled_settings = {
    'browser_monitoring.attributes.enabled': False }

_intrinsic_attributes = {
        'name': 'WebTransaction/Uri/'
}

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
@override_application_settings(_test_capture_attributes_disabled_settings)
def test_capture_attributes_disabled():
    settings = application_settings()

    assert settings.browser_monitoring.enabled
    assert not settings.browser_monitoring.attributes.enabled

    assert settings.js_agent_loader

    response = fully_featured_application.get('/')

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

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

    response = fully_featured_application.get('/')

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

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

    response = fully_featured_application.get('/')

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

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

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
def test_no_database_or_external_attributes_in_analytics():
    """Make no external calls or database calls in the transaction and check
    if the analytic event doesn't have the databaseCallCount, databaseDuration,
    externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    response = fully_featured_application.get('/')

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.string

    # Validate actual body content.

    assert content == 'RESPONSE'

_intrinsic_attributes = {
        'name': 'WebTransaction/Uri/db',
        'databaseCallCount': 2,
}

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
def test_database_attributes_in_analytics():
    """Make database calls in the transaction and check if the analytic
    event has the databaseCallCount and databaseDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    test_environ = {
                'db' : '2',
    }
    response = fully_featured_application.get('/db', extra_environ=test_environ)

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.string

    # Validate actual body content.

    assert content == 'RESPONSE'

_intrinsic_attributes = {
        'name': 'WebTransaction/Uri/ext',
        'externalCallCount': 2,
}

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
def test_external_attributes_in_analytics():
    """Make external calls in the transaction and check if the analytic
    event has the externalCallCount and externalDuration attributes.

    """
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    test_environ = {
                'external' : '2',
    }
    response = fully_featured_application.get('/ext',
            extra_environ=test_environ)

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.string

    # Validate actual body content.

    assert content == 'RESPONSE'

_intrinsic_attributes = {
        'name': 'WebTransaction/Uri/dbext',
        'databaseCallCount': 2,
        'externalCallCount': 2,
}

@validate_transaction_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
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
    response = fully_featured_application.get('/dbext',
            extra_environ=test_environ)

    # Validation of analytic data happens in the decorator.

    content = response.html.html.body.p.string

    # Validate actual body content.

    assert content == 'RESPONSE'

# -------------- Test background tasks ----------------

_expected_attributes = {
        'user': [],
        'agent': [],
        'intrinsic' : ('name', 'duration', 'type', 'timestamp', 'totalTime'),
}

_expected_absent_attributes = {
        'user': ('foo'),
        'agent': ('response.status', 'request.method'),
        'intrinsic': ('port'),
}

@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@background_task()
def test_background_task_intrinsics_has_no_port():
    pass
