import sys

from testing_support.fixtures import (validate_transaction_errors,
        override_application_settings, core_application_stats_engine,
        core_application_stats_engine_error, error_is_saved)

from newrelic.agent import (background_task, record_exception,
        application_settings, application, callable_name)
from newrelic.api.settings import STRIP_EXCEPTION_MESSAGE

_runtime_error_name = callable_name(RuntimeError)
_type_error_name = callable_name(TypeError)

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
