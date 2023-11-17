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
import time

import webtest

from testing_support.fixtures import (
    cat_enabled,
    make_cross_agent_headers,
    make_synthetics_header,
    override_application_settings,
    reset_core_stats_engine,
    validate_error_event_sample_data,
    validate_transaction_error_event_count,
)
from testing_support.sample_applications import fully_featured_app
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_non_transaction_error_event import (
    validate_non_transaction_error_event,
)

from newrelic.api.application import application_instance as application
from newrelic.api.application import application_settings
from newrelic.api.time_trace import notice_error
from newrelic.common.object_names import callable_name

# Error in test app hard-coded as a ValueError
SYNTHETICS_RESOURCE_ID = "09845779-16ef-4fa7-b7f2-44da8e62931c"
SYNTHETICS_JOB_ID = "8c7dd3ba-4933-4cbb-b1ed-b62f511782f4"
SYNTHETICS_MONITOR_ID = "dc452ae9-1a93-4ab5-8a33-600521e9cd00"

ERR_MESSAGE = "Transaction had bad value"
ERROR = ValueError(ERR_MESSAGE)

fully_featured_application = webtest.TestApp(fully_featured_app)

_intrinsic_attributes = {
    "error.class": callable_name(ERROR),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
    "transactionName": "WebTransaction/Uri/",
    "port": 80,  # SERVER_PORT default value in webtest WSGI environ
}


@validate_error_event_sample_data(required_attrs=_intrinsic_attributes, required_user_attrs=False)
@validate_transaction_error_event_count(num_errors=1)
def test_transaction_error_event_no_extra_attributes():
    test_environ = {"err_message": ERR_MESSAGE, "record_attributes": "FALSE"}
    response = fully_featured_application.get("/", extra_environ=test_environ)


_intrinsic_attributes = {
    "error.class": callable_name(ERROR),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
    "transactionName": "WebTransaction/Uri/",
    "databaseCallCount": 2,
    "externalCallCount": 2,
    "queueDuration": True,
    "port": 8888,
}


@validate_error_event_sample_data(required_attrs=_intrinsic_attributes, required_user_attrs=True)
def test_transaction_error_event_lotsa_attributes():
    test_environ = {
        "err_message": ERR_MESSAGE,
        "external": "2",
        "db": "2",
        "mod_wsgi.queue_start": ("t=%r" % time.time()),
        "SERVER_PORT": "8888",
    }
    response = fully_featured_application.get("/", extra_environ=test_environ)


_intrinsic_attributes = {
    "error.class": callable_name(ERROR),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
    "transactionName": "OtherTransaction/Uri/",
    "databaseCallCount": 2,
    "externalCallCount": 2,
    "queueDuration": False,
}


@validate_error_event_sample_data(required_attrs=_intrinsic_attributes, required_user_attrs=True)
def test_transaction_error_background_task():
    test_environ = {"err_message": ERR_MESSAGE, "external": "2", "db": "2", "newrelic.set_background_task": True}
    response = fully_featured_application.get("/", extra_environ=test_environ)


_intrinsic_attributes = {
    "error.class": callable_name(ERROR),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
    "transactionName": "WebTransaction/Uri/",
    "nr.referringTransactionGuid": 7,
}


@cat_enabled
@validate_error_event_sample_data(required_attrs=_intrinsic_attributes, required_user_attrs=True)
def test_transaction_error_cross_agent():
    test_environ = {
        "err_message": ERR_MESSAGE,
    }
    settings = application_settings()
    transaction_data = [7, 1, 77, "/path-hash"]
    headers = make_cross_agent_headers(transaction_data, settings.encoding_key, settings.cross_process_id)
    response = fully_featured_application.get("/", headers=headers, extra_environ=test_environ)


_intrinsic_attributes = {
    "error.class": callable_name(ERROR),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
    "transactionName": "WebTransaction/Uri/",
    "nr.syntheticsResourceId": SYNTHETICS_RESOURCE_ID,
    "nr.syntheticsJobId": SYNTHETICS_JOB_ID,
    "nr.syntheticsMonitorId": SYNTHETICS_MONITOR_ID,
}


@validate_error_event_sample_data(required_attrs=_intrinsic_attributes, required_user_attrs=True)
def test_transaction_error_with_synthetics():
    test_environ = {
        "err_message": ERR_MESSAGE,
    }
    settings = application_settings()
    headers = make_synthetics_header(
        settings.trusted_account_ids[0],
        SYNTHETICS_RESOURCE_ID,
        SYNTHETICS_JOB_ID,
        SYNTHETICS_MONITOR_ID,
        settings.encoding_key,
    )
    response = fully_featured_application.get("/", headers=headers, extra_environ=test_environ)


_intrinsic_attributes = {
    "error.class": callable_name(ERROR),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
    "transactionName": "WebTransaction/Uri/",
}


@validate_error_event_sample_data(required_attrs=_intrinsic_attributes, required_user_attrs=True, num_errors=2)
@validate_transaction_error_event_count(num_errors=2)
def test_multiple_errors_in_transaction():
    test_environ = {
        "err_message": ERR_MESSAGE,
        "n_errors": "2",
    }
    response = fully_featured_application.get("/", extra_environ=test_environ)


@override_application_settings({"error_collector.enabled": False})
@validate_error_event_sample_data(num_errors=0)
@validate_transaction_error_event_count(num_errors=0)
def test_error_collector_disabled():
    """If error_collector is disabled, don't event collect error info. There
    should be an empty result from transaction_node.error_event"""
    test_environ = {
        "err_message": ERR_MESSAGE,
    }
    response = fully_featured_application.get("/", extra_environ=test_environ)


@override_application_settings({"collect_error_events": False})
@validate_transaction_error_event_count(num_errors=0)
def test_collect_error_events_false():
    """Don't save error events to stats engine. Error info can be collected
    for error traces, so we only validate that event is not on stats engine,
    not that it can't be generated from the transaction node."""
    test_environ = {
        "err_message": ERR_MESSAGE,
    }
    response = fully_featured_application.get("/", extra_environ=test_environ)


@override_application_settings({"error_collector.capture_events": False})
@validate_transaction_error_event_count(num_errors=0)
def test_collect_error_capture_events_disabled():
    """Don't save error events to stats engine. Error info can be collected
    for error traces, so we only validate that event is not on stats engine,
    not that it can't be generated from the transaction node."""
    test_environ = {
        "err_message": ERR_MESSAGE,
    }
    response = fully_featured_application.get("/", extra_environ=test_environ)


# -------------- Test Error Events outside of transaction ----------------


class ErrorEventOutsideTransactionError(Exception):
    pass


outside_error = ErrorEventOutsideTransactionError(ERR_MESSAGE)

_intrinsic_attributes = {
    "error.class": callable_name(outside_error),
    "error.message": ERR_MESSAGE,
    "error.expected": False,
}


@reset_core_stats_engine()
@validate_non_transaction_error_event(_intrinsic_attributes)
def test_error_event_outside_transaction():
    try:
        raise outside_error
    except ErrorEventOutsideTransactionError:
        app = application()
        notice_error(sys.exc_info(), application=app)


_err_params = {"key": "value"}


@reset_core_stats_engine()
@validate_non_transaction_error_event(_intrinsic_attributes, required_user=_err_params)
def test_error_event_with_params_outside_transaction():
    try:
        raise outside_error
    except ErrorEventOutsideTransactionError:
        app = application()
        notice_error(sys.exc_info(), attributes=_err_params, application=app)


@reset_core_stats_engine()
@validate_non_transaction_error_event(_intrinsic_attributes, num_errors=2)
def test_multiple_error_events_outside_transaction():
    app = application()
    for i in range(2):
        try:
            raise ErrorEventOutsideTransactionError(ERR_MESSAGE + str(i))
        except ErrorEventOutsideTransactionError:
            notice_error(sys.exc_info(), application=app)


@reset_core_stats_engine()
@override_application_settings({"error_collector.enabled": False})
@validate_non_transaction_error_event(num_errors=0)
def test_error_event_outside_transaction_error_collector_disabled():
    try:
        raise outside_error
    except ErrorEventOutsideTransactionError:
        app = application()
        notice_error(sys.exc_info(), application=app)


@reset_core_stats_engine()
@override_application_settings({"error_collector.capture_events": False})
@validate_non_transaction_error_event(num_errors=0)
def test_error_event_outside_transaction_capture_events_disabled():
    try:
        raise outside_error
    except ErrorEventOutsideTransactionError:
        app = application()
        notice_error(sys.exc_info(), application=app)


@reset_core_stats_engine()
@override_application_settings({"collect_error_events": False})
@validate_non_transaction_error_event(num_errors=0)
def test_error_event_outside_transaction_collect_error_events_false():
    try:
        raise outside_error
    except ErrorEventOutsideTransactionError:
        app = application()
        notice_error(sys.exc_info(), application=app)
