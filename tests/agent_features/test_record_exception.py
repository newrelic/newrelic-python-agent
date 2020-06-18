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

from newrelic.api.application import (application_settings,
        application_instance as application)
from newrelic.api.background_task import background_task
from newrelic.api.settings import STRIP_EXCEPTION_MESSAGE
from newrelic.api.time_trace import record_exception

from newrelic.common.object_names import callable_name

from testing_support.fixtures import (validate_transaction_errors,
        override_application_settings, core_application_stats_engine_error,
        error_is_saved, reset_core_stats_engine, validate_application_errors,
        validate_transaction_error_trace_count,
        validate_application_error_trace_count,
        validate_transaction_error_event_count,
        validate_application_error_event_count)


_runtime_error_name = callable_name(RuntimeError)
_type_error_name = callable_name(TypeError)

# =============== Test errors during a transaction ===============

_test_record_exception_sys_exc_info = [
        (_runtime_error_name, 'one')]

@validate_transaction_errors(errors=_test_record_exception_sys_exc_info)
@background_task()
def test_record_exception_sys_exc_info():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception(*sys.exc_info())

_test_record_exception_no_exc_info = [
        (_runtime_error_name, 'one')]

@validate_transaction_errors(errors=_test_record_exception_no_exc_info)
@background_task()
def test_record_exception_no_exc_info():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception()

_test_record_exception_custom_params = [
        (_runtime_error_name, 'one')]

@validate_transaction_errors(errors=_test_record_exception_custom_params,
        required_params=[('key', 'value')])
@background_task()
def test_record_exception_custom_params():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception(*sys.exc_info(), params={'key': 'value'})

_test_record_exception_multiple_different_type = [
        (_runtime_error_name, 'one'),
        (_type_error_name, 'two')]

@validate_transaction_errors(errors=_test_record_exception_multiple_different_type)
@background_task()
def test_record_exception_multiple_different_type():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception()

    try:
        raise TypeError('two')
    except TypeError:
        record_exception()

_test_record_exception_multiple_same_type = [
        (_runtime_error_name, 'one'),
        (_runtime_error_name, 'two')]

@validate_transaction_errors(errors=_test_record_exception_multiple_same_type)
@background_task()
def test_record_exception_multiple_same_type():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception()

    try:
        raise RuntimeError('two')
    except RuntimeError:
        record_exception()

# =============== Test errors outside a transaction ===============

_test_application_exception = [
        (_runtime_error_name, 'one')]

@reset_core_stats_engine()
@validate_application_errors(errors=_test_application_exception)
def test_application_exception():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        application_instance = application()
        record_exception(application=application_instance)

_test_application_exception_sys_exc_info = [
        (_runtime_error_name, 'one')]

@reset_core_stats_engine()
@validate_application_errors(errors=_test_application_exception_sys_exc_info)
def test_application_exception_sys_exec_info():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        application_instance = application()
        record_exception(*sys.exc_info(), application=application_instance)

_test_application_exception_custom_params = [
        (_runtime_error_name, 'one')]

@reset_core_stats_engine()
@validate_application_errors(errors=_test_application_exception_custom_params,
        required_params=[('key', 'value')])
def test_application_exception_custom_params():
    try:
        raise RuntimeError('one')
    except RuntimeError:
        application_instance = application()
        record_exception(params={'key': 'value'},
                application=application_instance)

_test_application_exception_multiple = [
        (_runtime_error_name, 'one'),
        (_runtime_error_name, 'one')]

@reset_core_stats_engine()
@validate_application_errors(errors=_test_application_exception_multiple)
@background_task()
def test_application_exception_multiple():
    """Exceptions submitted straight to the stats engine doesn't check for
    duplicates
    """
    application_instance = application()
    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception(application=application_instance)

    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception(application=application_instance)

# =============== Test exception message stripping/whitelisting ===============

_test_record_exception_strip_message_disabled = [
        (_runtime_error_name, 'one')]

_strip_message_disabled_settings = {
        'strip_exception_messages.enabled': False,
}

@validate_transaction_errors(errors=_test_record_exception_strip_message_disabled)
@override_application_settings(_strip_message_disabled_settings)
@background_task()
def test_record_exception_strip_message_disabled():
    settings = application_settings()
    assert not settings.strip_exception_messages.enabled

    try:
        raise RuntimeError('one')
    except RuntimeError:
        record_exception()

class ErrorOne(Exception):
    message = 'error one message'

_error_one_name = callable_name(ErrorOne)

@override_application_settings(_strip_message_disabled_settings)
@background_task()
def test_record_exception_strip_message_disabled_outside_transaction():
    settings = application_settings()
    assert not settings.strip_exception_messages.enabled

    try:
        assert not error_is_saved(ErrorOne)
        raise ErrorOne(ErrorOne.message)
    except ErrorOne:
        application_instance = application()
        application_instance.record_exception()

    my_error = core_application_stats_engine_error(_error_one_name)
    assert my_error.message == ErrorOne.message

_test_record_exception_strip_message_enabled = [
        (_runtime_error_name, STRIP_EXCEPTION_MESSAGE)]

_strip_message_enabled_settings = {
        'strip_exception_messages.enabled': True,
}

@validate_transaction_errors(errors=_test_record_exception_strip_message_enabled)
@override_application_settings(_strip_message_enabled_settings)
@background_task()
def test_record_exception_strip_message_enabled():
    settings = application_settings()
    assert settings.strip_exception_messages.enabled

    try:
        raise RuntimeError('message not displayed')
    except RuntimeError:
        record_exception()

class ErrorTwo(Exception):
    message = 'error two message'

_error_two_name = callable_name(ErrorTwo)

@override_application_settings(_strip_message_enabled_settings)
@background_task()
def test_record_exception_strip_message_enabled_outside_transaction():
    settings = application_settings()
    assert settings.strip_exception_messages.enabled

    try:
        assert not error_is_saved(ErrorTwo)
        raise ErrorTwo(ErrorTwo.message)
    except ErrorTwo:
        application_instance = application()
        application_instance.record_exception()

    my_error = core_application_stats_engine_error(_error_two_name)
    assert my_error.message == STRIP_EXCEPTION_MESSAGE

_test_record_exception_strip_message_in_whitelist = [
        (_runtime_error_name, 'original error message')]

_strip_message_in_whitelist_settings = {
        'strip_exception_messages.enabled': True,
        'strip_exception_messages.whitelist': [_runtime_error_name],
}

@validate_transaction_errors(errors=_test_record_exception_strip_message_in_whitelist)
@override_application_settings(_strip_message_in_whitelist_settings)
@background_task()
def test_record_exception_strip_message_in_whitelist():
    settings = application_settings()
    assert settings.strip_exception_messages.enabled
    assert _runtime_error_name in settings.strip_exception_messages.whitelist

    try:
        raise RuntimeError('original error message')
    except RuntimeError:
        record_exception()

class ErrorThree(Exception):
    message = 'error three message'

_error_three_name = callable_name(ErrorThree)

_strip_message_in_whitelist_settings_outside_transaction = {
        'strip_exception_messages.enabled': True,
        'strip_exception_messages.whitelist': [_error_three_name],
}

@override_application_settings(
        _strip_message_in_whitelist_settings_outside_transaction)
@background_task()
def test_record_exception_strip_message_in_whitelist_outside_transaction():
    settings = application_settings()
    assert settings.strip_exception_messages.enabled
    assert _error_three_name in settings.strip_exception_messages.whitelist

    try:
        assert not error_is_saved(ErrorThree)
        raise ErrorThree(ErrorThree.message)
    except ErrorThree:
        application_instance = application()
        application_instance.record_exception()

    my_error = core_application_stats_engine_error(_error_three_name)
    assert my_error.message == ErrorThree.message

_test_record_exception_strip_message_not_in_whitelist = [
        (_runtime_error_name, STRIP_EXCEPTION_MESSAGE)]

_strip_message_not_in_whitelist_settings = {
        'strip_exception_messages.enabled': True,
        'strip_exception_messages.whitelist': ['FooError', 'BarError'],
}

@validate_transaction_errors(errors=_test_record_exception_strip_message_not_in_whitelist)
@override_application_settings(_strip_message_not_in_whitelist_settings)
@background_task()
def test_record_exception_strip_message_not_in_whitelist():
    settings = application_settings()
    assert settings.strip_exception_messages.enabled
    assert _runtime_error_name not in settings.strip_exception_messages.whitelist

    try:
        raise RuntimeError('message not displayed')
    except RuntimeError:
        record_exception()

class ErrorFour(Exception):
    message = 'error four message'

_error_four_name = callable_name(ErrorFour)

_strip_message_not_in_whitelist_settings_outside_transaction = {
        'strip_exception_messages.enabled': True,
        'strip_exception_messages.whitelist': ['ValueError', 'BarError'],
}

@override_application_settings(
        _strip_message_not_in_whitelist_settings_outside_transaction)
@background_task()
def test_record_exception_strip_message_not_in_whitelist_outside_transaction():
    settings = application_settings()
    assert settings.strip_exception_messages.enabled
    assert _error_four_name not in settings.strip_exception_messages.whitelist

    try:
        assert not error_is_saved(ErrorFour)
        raise ErrorFour(ErrorFour.message)
    except ErrorFour:
        application_instance = application()
        application_instance.record_exception()

    my_error = core_application_stats_engine_error(_error_four_name)
    assert my_error.message == STRIP_EXCEPTION_MESSAGE

# =============== Test exception limits ===============

def _raise_errors(num_errors, application=None):
    for i in range(num_errors):
        try:
            raise RuntimeError('error'+str(i))
        except RuntimeError:
            record_exception(application=application)

_errors_per_transaction_limit = 5
_num_errors_transaction = 6
_errors_per_harvest_limit = 20
_num_errors_app = 26
_error_event_limit = 25

@override_application_settings(
        {'agent_limits.errors_per_transaction': _errors_per_transaction_limit})
@validate_transaction_error_trace_count(_errors_per_transaction_limit)
@background_task()
def test_transaction_error_trace_limit():
    _raise_errors(_num_errors_transaction)

@override_application_settings(
        {'agent_limits.errors_per_harvest': _errors_per_harvest_limit})
@reset_core_stats_engine()
@validate_application_error_trace_count(_errors_per_harvest_limit)
def test_application_error_trace_limit():
    _raise_errors(_num_errors_app, application())

# The limit for errors on transactions is shared for traces and errors

@override_application_settings({
        'agent_limits.errors_per_transaction': _errors_per_transaction_limit,
        'error_collector.max_event_samples_stored': _error_event_limit})
@validate_transaction_error_event_count(_errors_per_transaction_limit)
@background_task()
def test_transaction_error_event_limit():
    _raise_errors(_num_errors_transaction)

# The harvest limit for error traces doesn't affect events

@override_application_settings({
        'agent_limits.errors_per_harvest': _errors_per_harvest_limit,
        'event_harvest_config.harvest_limits.error_event_data':
            _error_event_limit})
@reset_core_stats_engine()
@validate_application_error_event_count(_error_event_limit)
def test_application_error_event_limit():
    _raise_errors(_num_errors_app, application())

# =============== Test params is not a dict ===============

@reset_core_stats_engine()
@validate_transaction_error_trace_count(num_errors=1)
@background_task()
def test_transaction_record_exception_params_not_a_dict():
    try:
        raise RuntimeError()
    except RuntimeError:
        record_exception(*sys.exc_info(), params=[1,2,3])

@reset_core_stats_engine()
@validate_application_error_trace_count(num_errors=1)
def test_application_record_exception_params_not_a_dict():
    try:
        raise RuntimeError()
    except RuntimeError:
        record_exception(*sys.exc_info(), params=[1,2,3],
                application=application())
