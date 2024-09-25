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
import threading
import traceback

import pytest
from testing_support.fixtures import (
    override_application_settings,
    reset_core_stats_engine,
)
from testing_support.validators.validate_error_event_attributes import (
    validate_error_event_attributes,
)
from testing_support.validators.validate_error_event_attributes_outside_transaction import (
    validate_error_event_attributes_outside_transaction,
)
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_error_trace_attributes_outside_transaction import (
    validate_error_trace_attributes_outside_transaction,
)

from newrelic.api.application import application_instance as application
from newrelic.api.background_task import background_task
from newrelic.api.settings import set_error_group_callback
from newrelic.api.time_trace import notice_error
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import web_transaction
from newrelic.common.object_names import callable_name

_callback_called = threading.Event()
_truncated_value = "A" * 300


def error_group_callback(exc, data):
    _callback_called.set()

    if isinstance(exc, ValueError):
        return "value"
    elif isinstance(exc, ZeroDivisionError):
        return _truncated_value
    elif isinstance(exc, IndexError):
        return []
    elif isinstance(exc, LookupError):
        return 123
    elif isinstance(exc, TypeError):
        return ""


def test_clear_error_group_callback():
    settings = application().settings
    set_error_group_callback(lambda x, y: None)
    assert settings.error_collector.error_group_callback is not None, "Failed to set callback."
    set_error_group_callback(None)
    assert settings.error_collector.error_group_callback is None, "Failed to clear callback."


@pytest.mark.parametrize(
    "callback,accepted", [(error_group_callback, True), (lambda x, y: None, True), (None, False), ("string", False)]
)
def test_set_error_group_callback(callback, accepted):
    try:
        set_error_group_callback(callback)
        settings = application().settings
        if accepted:
            assert settings.error_collector.error_group_callback is not None, "Failed to set callback."
        else:
            assert settings.error_collector.error_group_callback is None, "Accepted bad callback."
    finally:
        set_error_group_callback(None)


@pytest.mark.parametrize(
    "exc_class,group_name,high_security",
    [
        (ValueError, "value", False),
        (ValueError, "value", True),
        (TypeError, None, False),
        (RuntimeError, None, False),
        (IndexError, None, False),
        (LookupError, None, False),
        (ZeroDivisionError, _truncated_value[:255], False),
    ],
    ids=("standard", "high-security", "empty-string", "None-value", "list-type", "int-type", "truncated-value"),
)
@reset_core_stats_engine()
def test_error_group_name_callback(exc_class, group_name, high_security):
    _callback_called.clear()

    if group_name is not None:
        exact = {"user": {}, "intrinsic": {}, "agent": {"error.group.name": group_name}}
        forgone = None
    else:
        exact = None
        forgone = {"user": [], "intrinsic": [], "agent": ["error.group.name"]}

    @validate_error_trace_attributes(callable_name(exc_class), forgone_params=forgone, exact_attrs=exact)
    @validate_error_event_attributes(forgone_params=forgone, exact_attrs=exact)
    @override_application_settings({"high_security": high_security})
    @background_task()
    def _test():

        try:
            raise exc_class()
        except Exception:
            notice_error()

        assert _callback_called.is_set()

    try:
        set_error_group_callback(error_group_callback)
        _test()
    finally:
        set_error_group_callback(None)


@pytest.mark.parametrize(
    "exc_class,group_name,high_security",
    [
        (ValueError, "value", False),
        (ValueError, "value", True),
        (TypeError, None, False),
        (RuntimeError, None, False),
        (IndexError, None, False),
        (LookupError, None, False),
        (ZeroDivisionError, _truncated_value[:255], False),
    ],
    ids=("standard", "high-security", "empty-string", "None-value", "list-type", "int-type", "truncated-value"),
)
@reset_core_stats_engine()
def test_error_group_name_callback_outside_transaction(exc_class, group_name, high_security):
    _callback_called.clear()

    if group_name is not None:
        exact = {"user": {}, "intrinsic": {}, "agent": {"error.group.name": group_name}}
        forgone = None
    else:
        exact = None
        forgone = {"user": [], "intrinsic": [], "agent": ["error.group.name"]}

    @validate_error_trace_attributes_outside_transaction(
        callable_name(exc_class), forgone_params=forgone, exact_attrs=exact
    )
    @validate_error_event_attributes_outside_transaction(forgone_params=forgone, exact_attrs=exact)
    @override_application_settings({"high_security": high_security})
    def _test():
        try:
            raise exc_class()
        except Exception:
            app = application()
            notice_error(application=app)

        assert _callback_called.is_set()

    try:
        set_error_group_callback(error_group_callback)
        _test()
    finally:
        set_error_group_callback(None)


@pytest.mark.parametrize(
    "transaction_decorator",
    [
        background_task(name="TestBackgroundTask"),
        web_transaction(
            name="TestWebTransaction",
            host="localhost",
            port=1234,
            request_method="GET",
            request_path="/",
            headers=[],
        ),
        None,
    ],
    ids=("background_task", "web_transation", "outside_transaction"),
)
@reset_core_stats_engine()
def test_error_group_name_callback_attributes(transaction_decorator):
    callback_errors = []
    _data = []

    def callback(error, data):
        def _callback():
            import types

            _data.append(data)
            txn = current_transaction()

            # Standard attributes
            assert isinstance(error, Exception)
            assert isinstance(data["traceback"], types.TracebackType)
            assert data["error.class"] is type(error)
            assert data["error.message"] == "text"
            assert data["error.expected"] is False

            # All attributes should always be included, but set to None when not relevant.
            if txn is None:  # Outside transaction
                assert data["transactionName"] is None
                assert data["custom_params"] == {"notice_error_attribute": 1}
                assert data["response.status"] is None
                assert data["request.method"] is None
                assert data["request.uri"] is None
            elif txn.background_task:  # Background task
                assert data["transactionName"] == "TestBackgroundTask"
                assert data["custom_params"] == {"notice_error_attribute": 1, "txn_attribute": 2}
                assert data["response.status"] is None
                assert data["request.method"] is None
                assert data["request.uri"] is None
            else:  # Web transaction
                assert data["transactionName"] == "TestWebTransaction"
                assert data["custom_params"] == {"notice_error_attribute": 1, "txn_attribute": 2}
                assert data["response.status"] == 200
                assert data["request.method"] == "GET"
                assert data["request.uri"] == "/"

        try:
            _callback()
        except Exception:
            callback_errors.append(sys.exc_info())
            raise

    def _test():
        try:
            txn = current_transaction()
            if txn:
                txn.add_custom_attribute("txn_attribute", 2)
                if not txn.background_task:
                    txn.process_response(200, [])
            raise Exception("text")
        except Exception:
            app = application() if transaction_decorator is None else None  # Only set outside transaction
            notice_error(application=app, attributes={"notice_error_attribute": 1})

        assert not callback_errors, "Callback inputs failed to validate.\nerror: %s\ndata: %s" % (
            traceback.format_exception(*callback_errors[0]),
            str(_data[0]),
        )

    if transaction_decorator is not None:
        _test = transaction_decorator(_test)  # Manually decorate test function

    try:
        set_error_group_callback(callback)
        _test()
    finally:
        set_error_group_callback(None)
