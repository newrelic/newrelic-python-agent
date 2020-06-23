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

import sys
import pytest
import webtest

from newrelic.api.background_task import background_task
from newrelic.api.transaction import (add_custom_parameter,
        add_custom_parameters)
from newrelic.api.wsgi_application import wsgi_application
from newrelic.core.attribute import (truncate, sanitize, Attribute,
    CastingFailureException, MAX_64_BIT_INT, _DESTINATIONS_WITH_EVENTS)

from newrelic.packages import six

from testing_support.fixtures import (override_application_settings,
    validate_attributes, validate_attributes_complete,
    validate_custom_parameters, validate_agent_attribute_types)
from testing_support.sample_applications import fully_featured_app


# Python 3 lacks longs

if sys.version_info >= (3, 0):
    long = int
try:
    from newrelic.core._thread_utilization import ThreadUtilization
except ImportError:
    ThreadUtilization = None


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'
    output = b'Hello World!'

    path = environ.get('PATH_INFO')
    if path == '/user_attribute':
        add_custom_parameter('test_key', 'test_value')

    response_headers = [('Content-Type', 'text/plain; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


_required_intrinsics = ['trip_id', 'totalTime']
_forgone_intrinsics = []


@validate_attributes('intrinsic', _required_intrinsics, _forgone_intrinsics)
def test_intrinsics():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/')
    assert response.body == b'Hello World!'


_required_agent = ['request.method', 'wsgi.output.seconds', 'response.status',
        'request.headers.host', 'request.headers.accept', 'request.uri',
        'response.headers.contentType', 'response.headers.contentLength']
if ThreadUtilization:
    _required_agent.append('thread.concurrency')
_forgone_agent = []


@validate_attributes('agent', _required_agent, _forgone_agent)
def test_agent():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/',
            extra_environ={'HTTP_ACCEPT': '*/*'})
    assert response.body == b'Hello World!'


_required_user = []
_forgone_user = ['test_key']


@validate_attributes('user', _required_user, _forgone_user)
def test_user_default():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/')
    assert response.body == b'Hello World!'


_required_user = ['test_key']
_forgone_user = []


@validate_attributes('user', _required_user, _forgone_user)
def test_user_add_attribute():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/user_attribute')
    assert response.body == b'Hello World!'


_settings_legacy_false = {'capture_params': False}
_required_request_legacy_false = []
_forgone_request_legacy_false = ['request.parameters.foo']


@override_application_settings(_settings_legacy_false)
@validate_attributes('agent', _required_request_legacy_false,
        _forgone_request_legacy_false)
def test_capture_request_params_legacy_false():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=bar')
    assert response.body == b'Hello World!'


_settings_legacy_true = {'capture_params': True}
_required_request_legacy_true = ['request.parameters.foo']
_forgone_request_legacy_true = []


@override_application_settings(_settings_legacy_true)
@validate_attributes('agent', _required_request_legacy_true,
        _forgone_request_legacy_true)
def test_capture_request_params_legacy_true():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=bar')
    assert response.body == b'Hello World!'


_required_request_default = ['request.parameters.foo']
_forgone_request_default = []


@validate_attributes('agent', _required_request_default,
        _forgone_request_default)
def test_capture_request_params_default():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=bar')
    assert response.body == b'Hello World!'


_required_display_host_default = []
_forgone_display_host_default = ['host.displayName']


@validate_attributes('agent', _required_display_host_default,
        _forgone_display_host_default)
def test_display_host_default():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/')
    assert response.body == b'Hello World!'


_settings_display_host_custom = {'process_host.display_name': 'CUSTOM NAME'}

_display_name_attribute = Attribute(name='host.displayName',
        value='CUSTOM NAME', destinations=_DESTINATIONS_WITH_EVENTS)
_required_display_host_custom = [_display_name_attribute]

_forgone_display_host_custom = []


@override_application_settings(_settings_display_host_custom)
@validate_attributes_complete('agent', _required_display_host_custom,
        _forgone_display_host_custom)
def test_display_host_custom():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/')
    assert response.body == b'Hello World!'


# Tests for truncate()

def test_truncate_string():
    s = 'blahblah'
    result = truncate(s, maxsize=4)
    assert isinstance(result, six.string_types)
    assert result == 'blah'


def test_truncate_bytes():
    b = b'foobar'
    result = truncate(b, maxsize=3)
    assert isinstance(result, six.binary_type)
    assert result == b'foo'


def test_truncate_unicode_snowman():
    # '\u2603' is 'SNOWMAN'
    u = u'snow\u2603'
    assert u.encode('utf-8') == b'snow\xe2\x98\x83'
    result = truncate(u, maxsize=5)
    assert isinstance(result, six.text_type)
    assert result == u'snow'


def test_truncate_combining_characters():
    # '\u0308' is 'COMBINING DIAERESIS' (AKA 'umlaut')
    u = u'Zoe\u0308'
    assert u.encode('utf-8') == b'Zoe\xcc\x88'

    # truncate will chop off 'COMBINING DIAERESIS', which leaves
    # 'LATIN SMALL LETTER E' by itself.

    result = truncate(u, maxsize=3)
    assert isinstance(result, six.text_type)
    assert result == u'Zoe'


def test_truncate_empty_string():
    s = ''
    result = truncate(s, maxsize=4)
    assert isinstance(result, six.string_types)
    assert result == ''


def test_truncate_empty_bytes():
    b = b''
    result = truncate(b, maxsize=3)
    assert isinstance(result, six.binary_type)
    assert result == b''


def test_truncate_empty_unicode():
    u = u''
    result = truncate(u, maxsize=5)
    assert isinstance(result, six.text_type)
    assert result == u''


# Tests for limits on user attributes

TOO_LONG = '*' * 256
TRUNCATED = '*' * 255


_required_custom_params = [('key', 'value')]
_forgone_custom_params = []


@validate_custom_parameters(_required_custom_params, _forgone_custom_params)
@background_task()
def test_custom_param_ok():
    result = add_custom_parameter('key', 'value')
    assert result


@validate_custom_parameters(_required_custom_params, _forgone_custom_params)
@background_task()
def test_custom_params_ok():
    result = add_custom_parameters([('key', 'value')])
    assert result


_required_custom_params_long_key = []
_forgone_custom_params_long_key = [(TOO_LONG, 'value')]


@validate_custom_parameters(_required_custom_params_long_key,
        _forgone_custom_params_long_key)
@background_task()
def test_custom_param_key_too_long():
    result = add_custom_parameter(TOO_LONG, 'value')
    assert not result


@validate_custom_parameters(_required_custom_params_long_key,
        _forgone_custom_params_long_key)
@background_task()
def test_custom_params_key_too_long():
    result = add_custom_parameters([(TOO_LONG, 'value')])
    assert not result


_required_custom_params_long_value = [('key', TRUNCATED)]
_forgone_custom_params_long_value = []


@validate_custom_parameters(_required_custom_params_long_value,
        _forgone_custom_params_long_value)
@background_task()
def test_custom_param_value_too_long():
    result = add_custom_parameter('key', TOO_LONG)
    assert result


@validate_custom_parameters(_required_custom_params_long_value,
        _forgone_custom_params_long_value)
@background_task()
def test_custom_params_value_too_long():
    result = add_custom_parameters([('key', TOO_LONG)])
    assert result


_required_custom_params_too_many = [('key-63', 'value')]
_forgone_custom_params_too_many = [('key-64', 'value')]


@validate_custom_parameters(_required_custom_params_too_many,
        _forgone_custom_params_too_many)
@background_task()
def test_custom_param_too_many():
    for i in range(65):
        result = add_custom_parameter('key-%02d' % i, 'value')
        if i < 64:
            assert result
        else:
            assert not result   # Last one fails


@validate_custom_parameters(_required_custom_params_too_many,
        _forgone_custom_params_too_many)
@background_task()
def test_custom_params_too_many():
    item_list = [('key-%02d' % i, 'value') for i in range(65)]
    result = add_custom_parameters(item_list)
    assert not result


_required_custom_params_name_not_string = []
_forgone_custom_params_name_not_string = [(1, 'value')]


@validate_custom_parameters(_required_custom_params_name_not_string,
        _forgone_custom_params_name_not_string)
@background_task()
def test_custom_param_name_not_string():
    result = add_custom_parameter(1, 'value')
    assert not result


@validate_custom_parameters(_required_custom_params_name_not_string,
        _forgone_custom_params_name_not_string)
@background_task()
def test_custom_params_name_not_string():
    result = add_custom_parameters([(1, 'value')])
    assert not result


TOO_BIG = MAX_64_BIT_INT + 1

_required_custom_params_int_too_big = []
_forgone_custom_params_int_too_big = [('key', TOO_BIG)]


@validate_custom_parameters(_required_custom_params_int_too_big,
        _forgone_custom_params_int_too_big)
@background_task()
def test_custom_param_int_too_big():
    result = add_custom_parameter('key', TOO_BIG)
    assert not result


@validate_custom_parameters(_required_custom_params_int_too_big,
        _forgone_custom_params_int_too_big)
@background_task()
def test_custom_params_int_too_big():
    result = add_custom_parameters([('key', TOO_BIG)])
    assert not result


OK_KEY = '*' * (255 - len('request.parameters.'))
OK_REQUEST_PARAM = 'request.parameters.' + OK_KEY
TOO_LONG_KEY = '*' * (256 - len('request.parameters.'))
TOO_LONG_REQUEST_PARAM = 'request.parameters.' + TOO_LONG_KEY

assert len(OK_REQUEST_PARAM) == 255
assert len(TOO_LONG_REQUEST_PARAM) == 256

_required_request_key_ok = [OK_REQUEST_PARAM]
_forgone_request_key_ok = []


@validate_attributes('agent', _required_request_key_ok,
        _forgone_request_key_ok)
def test_capture_request_params_key_ok():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?%s=bar' % OK_KEY)
    assert response.body == b'Hello World!'


_required_request_key_too_long = []
_forgone_request_key_too_long = [TOO_LONG_REQUEST_PARAM]


@validate_attributes('agent', _required_request_key_too_long,
        _forgone_request_key_too_long)
def test_capture_request_params_key_too_long():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?%s=bar' % TOO_LONG_KEY)
    assert response.body == b'Hello World!'


_required_request_value_too_long = ['request.parameters.foo']
_forgone_request_value_too_long = []


@validate_attributes('agent', _required_request_value_too_long,
        _forgone_request_value_too_long)
def test_capture_request_params_value_too_long():
    target_application = webtest.TestApp(target_wsgi_application)
    response = target_application.get('/?foo=%s' % TOO_LONG)
    assert response.body == b'Hello World!'


# Test attribute types are according to Agent-Attributes spec.

fully_featured_application = webtest.TestApp(fully_featured_app)

# Types are only defined in the spec for agent attributes, not intrinsics.

agent_attributes = {'request.headers.accept': six.string_types,
        'request.headers.contentLength': int,
        'request.headers.contentType': six.string_types,
        'request.headers.host': six.string_types,
        'request.headers.referer': six.string_types,
        'request.headers.userAgent': six.string_types,
        'request.method': six.string_types,
        'request.parameters.test': six.string_types,
        'response.headers.contentLength': int,
        'response.headers.contentType': six.string_types,
        'response.status': six.string_types}


@validate_agent_attribute_types(agent_attributes)
def test_agent_attribute_types():
    test_environ = {'CONTENT_TYPE': 'HTML', 'CONTENT_LENGTH': '100',
            'HTTP_USER_AGENT': 'Firefox', 'HTTP_REFERER': 'somewhere',
            'HTTP_ACCEPT': 'everything'}
    fully_featured_application.get('/?test=val', extra_environ=test_environ)


# Test sanitize()

def test_sanitize_string():
    s = 'foo'
    assert sanitize(s) == s


def test_sanitize_bytes():
    b = b'bytes'
    assert sanitize(b) == b


def test_sanitize_unicode():
    u = u'SMILING FACE: \u263a'
    assert sanitize(u) == u


def test_sanitize_bool():
    assert sanitize(True) is True


def test_sanitize_float():
    assert sanitize(1.11) == 1.11


def test_sanitize_int():
    assert sanitize(9876) == 9876


def test_sanitize_long():
    l = long(123456)
    assert sanitize(l) == l


def test_sanitize_dict():
    d = {1: 'foo'}
    assert sanitize(d) == "{1: 'foo'}"


def test_sanitize_list():
    l = [1, 2, 3, 4]
    assert sanitize(l) == '[1, 2, 3, 4]'


def test_sanitize_tuple():
    t = ('one', 'two', 'three')
    assert sanitize(t) == "('one', 'two', 'three')"


class Foo(object):
    pass


def test_sanitize_object():
    f = Foo()
    assert sanitize(f) == str(f)


class TypeErrorString(object):
    def __str__(self):
        return 42


def test_str_raises_type_error():
    with pytest.raises(CastingFailureException):
        sanitize(TypeErrorString())


class AttributeErrorString(object):
    def __str__(self):
        raise AttributeError()


def test_str_raises_attribute_error():
    with pytest.raises(CastingFailureException):
        sanitize(AttributeErrorString())
