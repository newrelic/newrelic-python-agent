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

import copy
import json
import logging
import os
import subprocess
import sys
import threading
import time

import pytest

try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from testing_support.sample_applications import (
    error_user_params_added,
    user_attributes_added,
)

from newrelic.admin.record_deploy import record_deploy
from newrelic.api.application import (
    application_instance,
    application_settings,
    register_application,
)
from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.encoding_utils import json_encode, obfuscate
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import (
    ObjectProxy,
    function_wrapper,
    transient_function_wrapper,
    wrap_function_wrapper,
)
from newrelic.config import initialize
from newrelic.core.agent import shutdown_agent
from newrelic.core.attribute import create_attributes
from newrelic.core.attribute_filter import (
    DST_ERROR_COLLECTOR,
    DST_TRANSACTION_TRACER,
    AttributeFilter,
)
from newrelic.core.config import apply_config_setting, flatten_settings, global_settings
from newrelic.network.exceptions import RetryDataForRequest
from newrelic.packages import six

_logger = logging.getLogger("newrelic.tests")


def _environ_as_bool(name, default=False):
    flag = os.environ.get(name, default)
    if default is None or default:
        try:
            flag = not flag.lower() in ["off", "false", "0"]
        except AttributeError:
            pass
    else:
        try:
            flag = flag.lower() in ["on", "true", "1"]
        except AttributeError:
            pass
    return flag


if _environ_as_bool("NEW_RELIC_HIGH_SECURITY"):
    DeveloperModeClient.RESPONSES["connect"]["high_security"] = True


def initialize_agent(app_name=None, default_settings=None):
    default_settings = default_settings or {}
    settings = global_settings()

    settings.app_name = "Python Agent Test"

    if "NEW_RELIC_LICENSE_KEY" not in os.environ:
        settings.developer_mode = True
        settings.license_key = "DEVELOPERMODELICENSEKEY"

    settings.startup_timeout = float(os.environ.get("NEW_RELIC_STARTUP_TIMEOUT", 20.0))
    settings.shutdown_timeout = float(os.environ.get("NEW_RELIC_SHUTDOWN_TIMEOUT", 20.0))

    # Disable the harvest thread during testing so that harvest is explicitly
    # called on test shutdown
    settings.debug.disable_harvest_until_shutdown = True

    if app_name is not None:
        settings.app_name = app_name

    for name, value in default_settings.items():
        apply_config_setting(settings, name, value)

    env_directory = os.environ.get("TOX_ENV_DIR", None)

    if env_directory is not None:
        log_directory = os.path.join(env_directory, "log")
    else:
        log_directory = "."

    log_file = os.path.join(log_directory, "python-agent-test.log")
    if "GITHUB_ACTIONS" in os.environ:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    try:
        os.unlink(log_file)
    except OSError:
        pass

    class FilteredStreamHandler(logging.StreamHandler):
        def emit(self, record):
            if len(logging.root.handlers) != 0:
                return

            if record.name.startswith("newrelic.packages"):
                return

            if record.levelno < logging.WARNING:
                return

            logging.StreamHandler.emit(self, record)

    _stdout_logger = logging.getLogger("newrelic")
    _stdout_handler = FilteredStreamHandler(sys.stderr)
    _stdout_format = "%(levelname)s - %(message)s"
    _stdout_formatter = logging.Formatter(_stdout_format)
    _stdout_handler.setFormatter(_stdout_formatter)
    _stdout_logger.addHandler(_stdout_handler)

    initialize(log_file=log_file, log_level=log_level, ignore_errors=False)


def capture_harvest_errors():
    queue = Queue()

    def wrap_harvest_loop(wrapped, instance, args, kwargs):
        try:
            return wrapped(*args, **kwargs)
        except Exception:
            exc_info = sys.exc_info()
            queue.put(exc_info)
            raise

    def wrap_shutdown_agent(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        if not queue.empty():
            exc_info = queue.get()
            raise exc_info[1]
        return result

    def wrap_record_custom_metric(wrapped, instance, args, kwargs):
        def _bind_params(name, value, *args, **kwargs):
            return name

        metric_name = _bind_params(*args, **kwargs)
        if (
            metric_name.startswith("Supportability/Python/Harvest/Exception")
            and not metric_name.endswith("DiscardDataForRequest")
            and not metric_name.endswith("RetryDataForRequest")
            and not metric_name.endswith(("newrelic.packages.urllib3.exceptions:ClosedPoolError"))
        ):
            exc_info = sys.exc_info()
            queue.put(exc_info)

        return wrapped(*args, **kwargs)

    # Capture all unhandled exceptions from the harvest thread

    wrap_function_wrapper("newrelic.core.agent", "Agent._harvest_loop", wrap_harvest_loop)

    # Treat custom exception metrics as unhandled errors

    wrap_function_wrapper("newrelic.core.stats_engine", "CustomMetrics.record_custom_metric", wrap_record_custom_metric)

    # Re-raise exceptions in the main thread

    wrap_function_wrapper("newrelic.core.agent", "Agent.shutdown_agent", wrap_shutdown_agent)


def collector_agent_registration_fixture(
    app_name=None, default_settings=None, linked_applications=None, should_initialize_agent=True
):
    default_settings = default_settings or {}
    linked_applications = linked_applications or []

    @pytest.fixture(scope="session")
    def _collector_agent_registration_fixture(request):
        if should_initialize_agent:
            initialize_agent(app_name=app_name, default_settings=default_settings)

        settings = global_settings()

        # Determine if should be using an internal fake local
        # collector for the test.

        use_fake_collector = _environ_as_bool("NEW_RELIC_FAKE_COLLECTOR", False)
        use_developer_mode = _environ_as_bool("NEW_RELIC_DEVELOPER_MODE", use_fake_collector)

        # Catch exceptions in the harvest thread and reraise them in the main
        # thread. This way the tests will reveal any unhandled exceptions in
        # either of the two agent threads.

        capture_harvest_errors()

        # Associate linked applications.

        application = application_instance()

        for name in linked_applications:
            application.link_to_application(name)

        # Force registration of the application.

        application = register_application()

        # Attempt to record deployment marker for test. It's ok
        # if the deployment marker does not record successfully.

        api_host = settings.host

        if api_host is None:
            api_host = "api.newrelic.com"
        elif api_host == "staging-collector.newrelic.com":
            api_host = "staging-api.newrelic.com"

        if not use_fake_collector and not use_developer_mode:
            description = os.path.basename(os.path.normpath(sys.prefix))
            try:
                _logger.debug("Record deployment marker host: %s", api_host)
                record_deploy(
                    host=api_host,
                    api_key=settings.api_key,
                    app_name=settings.app_name,
                    description=description,
                    port=settings.port or 443,
                    proxy_scheme=settings.proxy_scheme,
                    proxy_host=settings.proxy_host,
                    proxy_user=settings.proxy_user,
                    proxy_pass=settings.proxy_pass,
                    timeout=settings.agent_limits.data_collector_timeout,
                    ca_bundle_path=settings.ca_bundle_path,
                    disable_certificate_validation=settings.debug.disable_certificate_validation,
                )
            except Exception:
                _logger.exception("Unable to record deployment marker.")

        def finalize():
            shutdown_agent()

        request.addfinalizer(finalize)

        return application

    return _collector_agent_registration_fixture


@pytest.fixture(scope="function")
def collector_available_fixture(request, collector_agent_registration):
    application = application_instance()
    active = application.active
    assert active


def raise_background_exceptions(timeout=5.0):
    @function_wrapper
    def _raise_background_exceptions(wrapped, instance, args, kwargs):
        if getattr(raise_background_exceptions, "enabled", None) is None:
            raise_background_exceptions.event = threading.Event()
        else:
            assert raise_background_exceptions.count == 0

        raise_background_exceptions.enabled = True
        raise_background_exceptions.count = 0
        raise_background_exceptions.exception = None
        raise_background_exceptions.event.clear()

        try:
            result = wrapped(*args, **kwargs)

        except:
            # There was an exception in the immediate decorators.
            # Raise it rather than those from background threads.

            raise_background_exceptions.event.clear()
            raise_background_exceptions.exception = None
            raise

        else:
            # Immediate decorators completed normally. We need
            # though to make sure that background threads
            # completed within the timeout period and that no
            # exception occurred in the background threads.

            raise_background_exceptions.enabled = False

            done = raise_background_exceptions.event.is_set()
            raise_background_exceptions.event.clear()

            exc_info = raise_background_exceptions.exception
            raise_background_exceptions.exception = None

            assert done, "Timeout waiting for background task to finish."

            if exc_info is not None:
                six.reraise(*exc_info)

        return result

    return _raise_background_exceptions


def wait_for_background_threads(timeout=5.0):
    @function_wrapper
    def _wait_for_background_threads(wrapped, instance, args, kwargs):
        try:
            return wrapped(*args, **kwargs)
        finally:
            raise_background_exceptions.event.wait(timeout)

    return _wait_for_background_threads


@function_wrapper
def catch_background_exceptions(wrapped, instance, args, kwargs):
    if not getattr(raise_background_exceptions, "enabled", False):
        return wrapped(*args, **kwargs)

    raise_background_exceptions.count += 1

    try:
        return wrapped(*args, **kwargs)
    except:
        raise_background_exceptions.exception = sys.exc_info()
        raise
    finally:
        raise_background_exceptions.count -= 1
        if raise_background_exceptions.count == 0:
            raise_background_exceptions.event.set()


def make_cross_agent_headers(payload, encoding_key, cat_id):
    value = obfuscate(json_encode(payload), encoding_key)
    id_value = obfuscate(cat_id, encoding_key)
    return {"X-NewRelic-Transaction": value, "X-NewRelic-ID": id_value}


def make_synthetics_header(account_id, resource_id, job_id, monitor_id, encoding_key, version=1):
    value = [version, account_id, resource_id, job_id, monitor_id]
    value = obfuscate(json_encode(value), encoding_key)
    return {"X-NewRelic-Synthetics": value}


def capture_transaction_metrics(metrics_list, full_metrics=None):
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    @catch_background_exceptions
    def _capture_transaction_metrics(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            metrics = instance.stats_table
            if full_metrics is not None:
                full_metrics.update(metrics)
            for metric in metrics.keys():
                metrics_list.append(metric)
            metrics_list.sort()

        return result

    return _capture_transaction_metrics


def check_event_attributes(event_data, required_params=None, forgone_params=None, exact_attrs=None):
    """Check the event attributes from a single (first) event in a
    SampledDataSet. If necessary, clear out previous errors from StatsEngine
    prior to saving error, so that the desired error is the only one present
    in the data set.
    """
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    intrinsics, user_attributes, agent_attributes = next(iter(event_data))

    if required_params:
        for param in required_params["agent"]:
            assert param in agent_attributes, (param, agent_attributes)
        for param in required_params["user"]:
            assert param in user_attributes, (param, user_attributes)
        for param in required_params["intrinsic"]:
            assert param in intrinsics, (param, intrinsics)

    if forgone_params:
        for param in forgone_params["agent"]:
            assert param not in agent_attributes, (param, agent_attributes)
        for param in forgone_params["user"]:
            assert param not in user_attributes, (param, user_attributes)
        for param in forgone_params["intrinsic"]:
            assert param not in intrinsics, (param, intrinsics)

    if exact_attrs:
        for param, value in exact_attrs["agent"].items():
            assert agent_attributes[param] == value, ((param, value), agent_attributes)
        for param, value in exact_attrs["user"].items():
            assert user_attributes[param] == value, ((param, value), user_attributes)
        for param, value in exact_attrs["intrinsic"].items():
            assert intrinsics[param] == value, ((param, value), intrinsics)


def validate_request_params_omitted():
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_request_params(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        for attr in transaction.agent_attributes:
            assert not attr.name.startswith("request.parameters")

        return wrapped(*args, **kwargs)

    return _validate_request_params


def validate_attributes(attr_type, required_attr_names=None, forgone_attr_names=None):
    required_attr_names = required_attr_names or []
    forgone_attr_names = forgone_attr_names or []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_attributes(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        if attr_type == "intrinsic":
            attributes = transaction.trace_intrinsics
            attribute_names = attributes.keys()
        elif attr_type == "agent":
            attributes = transaction.agent_attributes
            attribute_names = [a.name for a in attributes]
            # validate that all agent attributes are included on the RootNode
            root_attribute_names = transaction.root.agent_attributes.keys()
            for name in attribute_names:
                assert name in root_attribute_names, name
        elif attr_type == "user":
            attributes = transaction.user_attributes
            attribute_names = [a.name for a in attributes]

            # validate that all user attributes are included on the RootNode
            root_attribute_names = transaction.root.user_attributes.keys()
            for name in attribute_names:
                assert name in root_attribute_names, name
        for name in required_attr_names:
            assert name in attribute_names, "name=%r, attributes=%r" % (name, attributes)

        for name in forgone_attr_names:
            assert name not in attribute_names, "name=%r, attributes=%r" % (name, attributes)

        return wrapped(*args, **kwargs)

    return _validate_attributes


def validate_attributes_complete(attr_type, required_attrs=None, forgone_attrs=None):
    # This differs from `validate_attributes` in that all fields of
    # Attribute must match (name, value, and destinations), not just
    # name. It's a more thorough test, but it's more of a pain to set
    # up, since you have to pass lists of Attributes to required_attrs
    # and forgone_attrs. For required destinations, the attribute will
    # match if at least the required destinations are present. For
    # forgone attributes the test will fail if any of the destinations
    # provided in the forgone attribute are found.
    #
    # Args:
    #
    #       attr_type: 'intrinsic' or 'agent' or 'user'
    #       required_attrs: List of Attributes that must be present.
    #       forgone_attrs: List of Attributes that must NOT be present.
    #
    # Note:
    #
    # The 'intrinsics' come from `transaction.trace_intrinsics`.

    required_attrs = required_attrs or []
    forgone_attrs = forgone_attrs or []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_attributes_complete(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        attribute_filter = transaction.settings.attribute_filter

        if attr_type == "intrinsic":
            # Intrinsics are stored as a dict, so for consistency's sake
            # in this test, we convert them to Attributes.

            items = transaction.trace_intrinsics
            attributes = create_attributes(items, DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER, attribute_filter)

        elif attr_type == "agent":
            attributes = transaction.agent_attributes

        elif attr_type == "user":
            attributes = transaction.user_attributes

        def _find_match(a, attributes):
            # Match by name and value. Ignore destination.
            return next((match for match in attributes if match.name == a.name and match.value == a.value), None)

        # Check that there is a name/value match, and that the destinations
        # for the matched attribute include the ones in required.

        for required in required_attrs:
            match = _find_match(required, attributes)
            assert match, "required=%r, attributes=%r" % (required, attributes)

            result_dest = required.destinations & match.destinations
            assert result_dest == required.destinations, "required=%r, attributes=%r" % (required, attributes)

        # Check that the name and value are NOT going to ANY of the
        # destinations provided as forgone, either because there is no
        # name/value match, or because there is a name/value match, but
        # the destinations do not include the ones in forgone.

        for forgone in forgone_attrs:
            match = _find_match(forgone, attributes)

            if match:
                result_dest = forgone.destinations & match.destinations
                assert result_dest == 0, "forgone=%r, attributes=%r" % (forgone, attributes)

        return wrapped(*args, **kwargs)

    return _validate_attributes_complete


def validate_agent_attribute_types(required_attrs):
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_agent_attribute_types(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        attributes = transaction.agent_attributes
        attr_vals = {}
        for attr in attributes:
            attr_vals[attr.name] = attr.value

        for attr_name, attr_type in required_attrs.items():
            assert attr_name in attr_vals
            assert isinstance(attr_vals[attr_name], attr_type)

        return wrapped(*args, **kwargs)

    return _validate_agent_attribute_types


def validate_transaction_event_sample_data(required_attrs, required_user_attrs=True):
    """This test depends on values in the test application from
    agent_features/test_analytics.py, and is only meant to be run as a
    validation with those tests.
    """

    add_transaction_called = []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        @transient_function_wrapper("newrelic.core.stats_engine", "SampledDataSet.add")
        def _validate_transaction_event_sample_data(wrapped, instance, args, kwargs):
            def _bind_params(sample, *args, **kwargs):
                return sample

            sample = _bind_params(*args, **kwargs)

            assert isinstance(sample, list)
            assert len(sample) == 3

            intrinsics, user_attributes, _ = sample

            if intrinsics["type"] != "Transaction":
                return wrapped(*args, **kwargs)  # Exit early

            add_transaction_called.append(True)

            assert intrinsics["name"] == required_attrs["name"]

            # check that error event intrinsics haven't bled in

            assert "error.class" not in intrinsics
            assert "error.message" not in intrinsics
            assert "error.expected" not in intrinsics
            assert "transactionName" not in intrinsics

            _validate_event_attributes(
                intrinsics,
                user_attributes,
                required_attrs,
                required_user_attrs,
            )

            return wrapped(*args, **kwargs)

        result = _validate_transaction_event_sample_data(wrapped)(*args, **kwargs)
        assert add_transaction_called
        return result

    return _validate_wrapper


def validate_transaction_error_event_count(num_errors=1):
    """Validate that the correct number of error events are saved to StatsEngine
    after a transaction
    """

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_error_event_on_stats_engine(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            error_events = list(instance.error_events)
            assert len(error_events) == num_errors

        return result

    return _validate_error_event_on_stats_engine


def validate_transaction_error_trace_count(num_errors):
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_transaction_error_trace_count(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            traced_errors = instance.error_data()
            assert len(traced_errors) == num_errors

        return result

    return _validate_transaction_error_trace_count


def validate_stats_engine_explain_plan_output_is_none():
    """This fixture isn't useful by itself, because you need to generate
    explain plans, which doesn't normally occur during record_transaction().

    Use the `validate_transaction_slow_sql_count` fixture to force the
    generation of slow sql data after record_transaction(), which will run
    newrelic.core.stats_engine.explain_plan.

    """

    @transient_function_wrapper("newrelic.core.stats_engine", "explain_plan")
    def _validate_explain_plan_output_is_none(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            assert result is None

        return result

    return _validate_explain_plan_output_is_none


def validate_error_event_sample_data(required_attrs=None, required_user_attrs=True, num_errors=1):
    """Validate the data collected for error_events. This test depends on values
    in the test application from agent_features/test_analytics.py, and is only
    meant to be run as a validation with those tests.
    """
    required_attrs = required_attrs or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_error_event_sample_data(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            def _bind_params(transaction, *args, **kwargs):
                return transaction

            transaction = _bind_params(*args, **kwargs)

            error_events = transaction.error_events(instance.stats_table)
            assert len(error_events) == num_errors
            for sample in error_events:
                assert isinstance(sample, list)
                assert len(sample) == 3

                intrinsics, user_attributes, _ = sample

                # These intrinsics should always be present

                assert intrinsics["type"] == "TransactionError"
                assert intrinsics["transactionName"] == required_attrs["transactionName"]
                assert intrinsics["error.class"] == required_attrs["error.class"]
                assert intrinsics["error.message"].startswith(required_attrs["error.message"])
                assert intrinsics["error.expected"] == required_attrs["error.expected"]
                assert intrinsics["nr.transactionGuid"] is not None
                assert intrinsics["spanId"] is not None

                # check that transaction event intrinsics haven't bled in

                assert "name" not in intrinsics

                _validate_event_attributes(intrinsics, user_attributes, required_attrs, required_user_attrs)
                if required_user_attrs:
                    error_user_params = error_user_params_added()
                    for param, value in error_user_params.items():
                        assert user_attributes[param] == value

        return result

    return _validate_error_event_sample_data


def _validate_event_attributes(intrinsics, user_attributes, required_intrinsics, required_user):
    now = time.time()
    assert isinstance(intrinsics["timestamp"], int)
    assert intrinsics["timestamp"] <= 1000.0 * now
    assert intrinsics["duration"] >= 0.0

    assert "memcacheDuration" not in intrinsics

    if required_user:
        required_user_attributes = user_attributes_added()
        for attr, value in required_user_attributes.items():
            assert user_attributes[attr] == value
    else:
        assert user_attributes == {}

    if "databaseCallCount" in required_intrinsics:
        assert intrinsics["databaseDuration"] > 0
        call_count = required_intrinsics["databaseCallCount"]
        assert intrinsics["databaseCallCount"] == call_count
    else:
        assert "databaseDuration" not in intrinsics
        assert "databaseCallCount" not in intrinsics

    if "externalCallCount" in required_intrinsics:
        assert intrinsics["externalDuration"] > 0
        call_count = required_intrinsics["externalCallCount"]
        assert intrinsics["externalCallCount"] == call_count
    else:
        assert "externalDuration" not in intrinsics
        assert "externalCallCount" not in intrinsics

    if intrinsics.get("queueDuration", False):
        assert intrinsics["queueDuration"] > 0
    else:
        assert "queueDuration" not in intrinsics

    if "nr.referringTransactionGuid" in required_intrinsics:
        guid = required_intrinsics["nr.referringTransactionGuid"]
        assert intrinsics["nr.referringTransactionGuid"] == guid
    else:
        assert "nr.referringTransactionGuid" not in intrinsics

    if "nr.syntheticsResourceId" in required_intrinsics:
        res_id = required_intrinsics["nr.syntheticsResourceId"]
        job_id = required_intrinsics["nr.syntheticsJobId"]
        monitor_id = required_intrinsics["nr.syntheticsMonitorId"]
        assert intrinsics["nr.syntheticsResourceId"] == res_id
        assert intrinsics["nr.syntheticsJobId"] == job_id
        assert intrinsics["nr.syntheticsMonitorId"] == monitor_id

    if "port" in required_intrinsics:
        assert intrinsics["port"] == required_intrinsics["port"]


def validate_transaction_exception_message(expected_message):
    """Test exception message encoding/decoding for a single error"""

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_transaction_exception_message(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            error_data = instance.error_data()
            assert len(error_data) == 1
            error = error_data[0]

            # make sure we have the one error we are testing

            # Because we ultimately care what is sent to APM, run the exception
            # data through the encoding code that is would be run through
            # before being sent to the collector.

            encoded_error = json_encode(error)

            # to decode, use un-adultered json loading methods

            decoded_json = json.loads(encoded_error)

            message = decoded_json[2]
            assert expected_message == message

        return result

    return _validate_transaction_exception_message


def validate_application_exception_message(expected_message):
    """Test exception message encoding/decoding for a single error"""

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.notice_error")
    def _validate_application_exception_message(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            error_data = instance.error_data()
            assert len(error_data) == 1
            error = error_data[0]

            # make sure we have the one error we are testing

            # Because we ultimately care what is sent to APM, run the exception
            # data through the encoding code that is would be run through
            # before being sent to the collector.

            encoded_error = json_encode(error)

            # to decode, use un-adultered json loading methods

            decoded_json = json.loads(encoded_error)

            message = decoded_json[2]
            assert expected_message == message

        return result

    return _validate_application_exception_message


def _validate_custom_event(recorded_event, required_event):
    assert len(recorded_event) == 2  # [intrinsic, user attributes]

    intrinsics = recorded_event[0]

    assert intrinsics["type"] == required_event[0]["type"]

    now = time.time()
    assert isinstance(intrinsics["timestamp"], int)
    assert intrinsics["timestamp"] <= 1000.0 * now
    assert intrinsics["timestamp"] >= 1000.0 * required_event[0]["timestamp"]

    assert recorded_event[1].items() == required_event[1].items()


def validate_custom_event_in_application_stats_engine(required_event):
    @function_wrapper
    def _validate_custom_event_in_application_stats_engine(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            stats = core_application_stats_engine(None)
            assert stats.custom_events.num_samples == 1

            custom_event = next(iter(stats.custom_events))
            _validate_custom_event(custom_event, required_event)

        return result

    return _validate_custom_event_in_application_stats_engine


def validate_custom_event_count(count):
    @function_wrapper
    def _validate_custom_event_count(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            stats = core_application_stats_engine(None)
            assert stats.custom_events.num_samples == count

        return result

    return _validate_custom_event_count


def _validate_node_parenting(node, expected_node):
    assert node.exclusive >= 0, "node.exclusive = %s" % node.exclusive

    expected_children = expected_node[1]

    def len_error():
        return ("len(node.children)=%s, len(expected_children)=%s, node.children=%s") % (
            len(node.children),
            len(expected_children),
            node.children,
        )

    assert len(node.children) == len(expected_children), len_error()

    for index, child in enumerate(node.children):
        assert child.start_time > node.start_time
        _validate_node_parenting(child, expected_children[index])


def validate_tt_parenting(expected_parenting):
    """
    Validate the parenting and start_time of each node in a transaction trace

    expected_parenting is a tuple. The second item is a list of child nodes.
    The first item is not used in validation and exists as a tool for the
    developer to differentiate the node tuples.

        expected_parenting_example = (
            'TransactionNode', [
                ('FunctionNode', [
                    ('FunctionNode', [
                        ('FunctionNode', []),
                        ('FunctionNode', []),
                    ]),
            ]),
        ])
    """

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_tt_parenting(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        finally:

            def _bind_params(transaction, *args, **kwargs):
                return transaction

            transaction = _bind_params(*args, **kwargs)
            _validate_node_parenting(transaction.root, expected_parenting)

        return result

    return _validate_tt_parenting


def override_application_name(app_name):
    # The argument here cannot be named 'name', or else it triggers
    # a PyPy bug. Hence, we use 'app_name' instead.

    class Application(ObjectProxy):
        @property
        def name(self):
            return app_name

    @transient_function_wrapper("newrelic.api.transaction", "Transaction.__init__")
    def _override_application_name(wrapped, instance, args, kwargs):
        def _bind_params(application, *args, **kwargs):
            return application, args, kwargs

        application, _args, _kwargs = _bind_params(*args, **kwargs)

        application = Application(application)

        return wrapped(application, *_args, **_kwargs)

    return _override_application_name


@function_wrapper
def dt_enabled(wrapped, instance, args, kwargs):
    @transient_function_wrapper("newrelic.core.adaptive_sampler", "AdaptiveSampler.compute_sampled")
    def force_sampled(wrapped, instance, args, kwargs):
        wrapped(*args, **kwargs)
        return True

    settings = {"distributed_tracing.enabled": True}
    wrapped = override_application_settings(settings)(wrapped)
    wrapped = force_sampled(wrapped)

    return wrapped(*args, **kwargs)  # pylint: disable=E1102


@function_wrapper
def cat_enabled(wrapped, instance, args, kwargs):
    settings = {"cross_application_tracer.enabled": True, "distributed_tracing.enabled": False}
    wrapped = override_application_settings(settings)(wrapped)

    return wrapped(*args, **kwargs)


def override_application_settings(overrides):
    @function_wrapper
    def _override_application_settings(wrapped, instance, args, kwargs):
        # The settings object has references from a number of
        # different places. We have to create a copy, overlay
        # the temporary settings and then when done clear the
        # top level settings object and rebuild it when done.
        original_settings = application_settings()
        backup = copy.deepcopy(original_settings.__dict__)

        try:
            for name, value in overrides.items():
                apply_config_setting(original_settings, name, value)

            # should also update the attribute filter since it is affected
            # by application settings

            flat_settings = flatten_settings(original_settings)
            original_settings.attribute_filter = AttributeFilter(flat_settings)

            return wrapped(*args, **kwargs)
        finally:
            original_settings.__dict__.clear()
            original_settings.__dict__.update(backup)

    return _override_application_settings


def override_generic_settings(settings_object, overrides):
    @function_wrapper
    def _override_generic_settings(wrapped, instance, args, kwargs):
        # In some cases, a settings object may have references
        # from a number of different places. We have to create
        # a copy, overlay the temporary settings and then when
        # done, clear the top level settings object and rebuild
        # it when done.
        original = settings_object
        backup = copy.deepcopy(original.__dict__)

        try:
            for name, value in overrides.items():
                apply_config_setting(original, name, value)
            return wrapped(*args, **kwargs)
        finally:
            original.__dict__.clear()
            original.__dict__.update(backup)

    return _override_generic_settings


def override_ignore_status_codes(status_codes):
    @function_wrapper
    def _override_ignore_status_codes(wrapped, instance, args, kwargs):
        # Updates can be made to ignored status codes in server
        # side configs. Changes will be applied to application
        # settings so we first check there and if they don't
        # exist, we default to global settings

        application = application_instance()
        settings = application and application.settings

        if not settings:
            settings = global_settings()

        original = settings.error_collector.ignore_status_codes

        try:
            settings.error_collector.ignore_status_codes = status_codes
            return wrapped(*args, **kwargs)
        finally:
            settings.error_collector.ignore_status_codes = original

    return _override_ignore_status_codes


def override_expected_status_codes(status_codes):
    @function_wrapper
    def _override_expected_status_codes(wrapped, instance, args, kwargs):
        # Updates can be made to expected status codes in server
        # side configs. Changes will be applied to application
        # settings so we first check there and if they don't
        # exist, we default to global settings

        application = application_instance()
        settings = application and application.settings

        if not settings:
            settings = global_settings()

        original = settings.error_collector.expected_status_codes

        try:
            settings.error_collector.expected_status_codes = status_codes
            return wrapped(*args, **kwargs)
        finally:
            settings.error_collector.expected_status_codes = original

    return _override_expected_status_codes


def reset_core_stats_engine():
    """Reset the StatsEngine and custom StatsEngine of the core application."""

    @function_wrapper
    def _reset_core_stats_engine(wrapped, instance, args, kwargs):
        api_application = application_instance()
        api_name = api_application.name
        core_application = api_application._agent.application(api_name)

        stats = core_application._stats_engine
        stats.reset_stats(stats.settings)

        custom_stats = core_application._stats_custom_engine
        custom_stats.reset_stats(custom_stats.settings)

        return wrapped(*args, **kwargs)

    return _reset_core_stats_engine


def core_application_stats_engine(app_name=None):
    """Return the StatsEngine object from the core application object.

    Useful when validating items added outside of a transaction, since
    monkey-patching StatsEngine.record_transaction() doesn't work in
    those situations.

    """

    api_application = application_instance(app_name)
    api_name = api_application.name
    core_application = api_application._agent.application(api_name)
    return core_application._stats_engine


def core_application_stats_engine_error(error_type, app_name=None):
    """Return a single error with the type of error_type, or None.

    In the core application StatsEngine, look in StatsEngine.error_data()
    and return the first error with the type of error_type. If none found,
    return None.

    Useful for verifying that application.notice_error() works, since
    the error is saved outside of a transaction. Must use a unique error
    type per test in a single test file, so that it returns the error you
    expect. (If you have 2 tests that record the same type of exception, then
    StatsEngine.error_data() will contain 2 errors with the same type, but
    this function will always return the first one it finds.)

    """

    stats = core_application_stats_engine(app_name)
    errors = stats.error_data()
    return next((e for e in errors if e.type == error_type), None)


def error_is_saved(error, app_name=None):
    """Return True, if an error of a particular type has already been saved.

    Before calling application.notice_error() in a test, it's good to
    check if that type of error has already been saved, so you know that
    there will only be a single example of a type of Error in error_data()
    when you verify that the exception was recorded correctly.

    Example usage:

        try:
            assert not error_is_saved(ErrorOne)
            raise ErrorOne('error one message')
        except ErrorOne:
            application_instance = application()
            application_instance.notice_error()

        my_error = core_application_stats_engine_error(_error_one_name)
        assert my_error.message == 'error one message'

    """

    error_name = callable_name(error)
    stats = core_application_stats_engine(app_name)
    errors = stats.error_data()
    return error_name in [e.type for e in errors if e.type == error_name]


def set_default_encoding(encoding):
    """Changes the default encoding of the global environment. Only works in
    Python 2, will cause an error in Python 3
    """

    # If using this with other decorators/fixtures that depend on the system
    # default encoding, this decorator must be on wrapped on top of them.

    @function_wrapper
    def _set_default_encoding(wrapped, instance, args, kwargs):
        # This technique of reloading the sys module is necessary because the
        # method is removed during initialization of Python. Doing this is
        # highly frowned upon, but it is the only way to test how our agent
        # behaves when different sys encodings are used. For more information,
        # see this Stack Overflow post: http://bit.ly/1xBNxRc

        six.moves.reload_module(sys)  # pylint: disable=E1101
        original_encoding = sys.getdefaultencoding()
        sys.setdefaultencoding(encoding)  # pylint: disable=E1101

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        finally:
            sys.setdefaultencoding(original_encoding)  # pylint: disable=E1101

        return result

    return _set_default_encoding


def function_not_called(module, name):
    """Verify that a function is not called.

    Assert False, if it is.

    """

    called = []

    @transient_function_wrapper(module, name)
    def _function_not_called_(wrapped, instance, args, kwargs):
        called.append(True)
        return wrapped(*args, **kwargs)

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        new_wrapper = _function_not_called_(wrapped)
        result = new_wrapper(*args, **kwargs)
        assert not called
        return result

    return wrapper


def validate_analytics_catmap_data(name, expected_attributes=(), non_expected_attributes=()):
    samples = []

    @transient_function_wrapper("newrelic.core.stats_engine", "SampledDataSet.add")
    def _capture_samples(wrapped, instance, args, kwargs):
        def _bind_params(sample, *args, **kwargs):
            return sample

        sample = _bind_params(*args, **kwargs)
        samples.append(sample)
        return wrapped(*args, **kwargs)

    @function_wrapper
    def _validate_analytics_sample_data(wrapped, instance, args, kwargs):
        _new_wrapped = _capture_samples(wrapped)

        result = _new_wrapped(*args, **kwargs)
        # Check type of s[0] because it returns an integer if s is a LogEventNode
        _samples = [s for s in samples if not isinstance(s[0], int) and s[0]["type"] == "Transaction"]
        assert _samples, "No Transaction events captured."
        for sample in _samples:
            assert isinstance(sample, list)
            assert len(sample) == 3

            intrinsics, _, _ = sample

            assert intrinsics["type"] == "Transaction"
            assert intrinsics["name"] == name
            assert intrinsics["timestamp"] >= 0.0
            assert intrinsics["duration"] >= 0.0

            for key, value in expected_attributes.items():
                assert intrinsics[key] == value

            for key in non_expected_attributes:
                assert intrinsics.get(key) is None

        return result

    return _validate_analytics_sample_data


def count_transactions(count_list):
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _increment_count(wrapped, instance, args, kwargs):
        count_list.append(True)
        return wrapped(*args, **kwargs)

    return _increment_count


def failing_endpoint(endpoint, raises=RetryDataForRequest, call_number=1):
    called_list = []

    @transient_function_wrapper("newrelic.core.agent_protocol", "AgentProtocol.send")
    def send_request_wrapper(wrapped, instance, args, kwargs):
        def _bind_params(method, *args, **kwargs):
            return method

        method = _bind_params(*args, **kwargs)

        if method == endpoint:
            called_list.append(True)
            if len(called_list) == call_number:
                raise raises()

        return wrapped(*args, **kwargs)

    return send_request_wrapper


def check_attributes(parameters, required_params=None, forgone_params=None, exact_attrs=None):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    intrinsics = parameters.get("intrinsics", {})
    user_attributes = parameters.get("userAttributes", {})
    agent_attributes = parameters.get("agentAttributes", {})

    if required_params:
        for param in required_params["agent"]:
            assert param in agent_attributes, (param, agent_attributes)
        for param in required_params["user"]:
            assert param in user_attributes, (param, user_attributes)
        for param in required_params["intrinsic"]:
            assert param in intrinsics, (param, intrinsics)

    if forgone_params:
        for param in forgone_params["agent"]:
            assert param not in agent_attributes, (param, agent_attributes)
        for param in forgone_params["user"]:
            assert param not in user_attributes, (param, user_attributes)
        for param in forgone_params["intrinsic"]:
            assert param not in intrinsics, (param, intrinsics)

    if exact_attrs:
        for param, value in exact_attrs["agent"].items():
            assert agent_attributes[param] == value, ((param, value), agent_attributes)
        for param, value in exact_attrs["user"].items():
            assert user_attributes[param] == value, ((param, value), user_attributes)
        for param, value in exact_attrs["intrinsic"].items():
            assert intrinsics[param] == value, ((param, value), intrinsics)


def check_error_attributes(
    parameters, required_params=None, forgone_params=None, exact_attrs=None, is_transaction=True
):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    parameter_fields = ["userAttributes"]
    if is_transaction:
        parameter_fields.extend(["stack_trace", "agentAttributes", "intrinsics"])

    for field in parameter_fields:
        assert field in parameters

    # we can remove this after agent attributes transition is all over
    assert "parameter_groups" not in parameters
    assert "custom_params" not in parameters
    assert "request_params" not in parameters
    assert "request_uri" not in parameters

    check_attributes(parameters, required_params, forgone_params, exact_attrs)


class Environ(object):
    """Context manager for setting environment variables temporarily."""

    def __init__(self, **kwargs):
        self._original_environ = os.environ
        self._environ_dict = kwargs

    def __enter__(self):
        for key, val in self._environ_dict.items():
            os.environ[key] = str(val)

    def __exit__(self, type, value, traceback):  # pylint: disable=redefined-builtin
        os.environ.clear()
        os.environ = self._original_environ


class TerminatingPopen(subprocess.Popen):
    """Context manager will terminate process when exiting, instead of waiting."""

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):  # pylint: disable=redefined-builtin,arguments-differ
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()

        self.terminate()


@pytest.fixture()
def newrelic_caplog(caplog):
    logger = logging.getLogger("newrelic")
    logger.propagate = True

    yield caplog
