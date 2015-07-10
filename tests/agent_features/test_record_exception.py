import sys

from testing_support.fixtures import (validate_transaction_errors,
        override_application_settings)

from newrelic.agent import (background_task, record_exception,
        application_settings)
from newrelic.api.transaction import STRIP_EXCEPTION_MESSAGE

_runtime_error_name = (RuntimeError.__module__ + ':' + RuntimeError.__name__)
_type_error_name = (TypeError.__module__ + ':' + TypeError.__name__)

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
