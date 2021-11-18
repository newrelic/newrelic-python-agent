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
from newrelic.common.encoding_utils import (
    deobfuscate,
    json_decode,
    json_encode,
    obfuscate,
    unpack_field,
)
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import (
    ObjectProxy,
    function_wrapper,
    transient_function_wrapper,
    wrap_function_wrapper,
)
from newrelic.common.system_info import LOCALHOST_EQUIVALENTS
from newrelic.config import initialize
from newrelic.core.agent import shutdown_agent
from newrelic.core.attribute import create_attributes
from newrelic.core.attribute_filter import (
    DST_ERROR_COLLECTOR,
    DST_TRANSACTION_TRACER,
    AttributeFilter,
)
from newrelic.core.config import apply_config_setting, flatten_settings, global_settings
from newrelic.core.database_utils import SQLConnections
from newrelic.core.internal_metrics import InternalTraceContext
from newrelic.core.stats_engine import CustomMetrics
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


def _lookup_string_table(name, string_table, default=None):
    try:
        index = int(name.lstrip("`"))
        return string_table[index]
    except ValueError:
        return default


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

    env_directory = os.environ.get("TOX_ENVDIR", None)

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
def collector_available_fixture(request):
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


def validate_transaction_metrics(
    name,
    group="Function",
    background_task=False,
    scoped_metrics=None,
    rollup_metrics=None,
    custom_metrics=None,
    index=-1,
):
    scoped_metrics = scoped_metrics or []
    rollup_metrics = rollup_metrics or []
    custom_metrics = custom_metrics or []

    if background_task:
        unscoped_metrics = [
            "OtherTransaction/all",
            "OtherTransaction/%s/%s" % (group, name),
            "OtherTransactionTotalTime",
            "OtherTransactionTotalTime/%s/%s" % (group, name),
        ]
        transaction_scope_name = "OtherTransaction/%s/%s" % (group, name)
    else:
        unscoped_metrics = [
            "WebTransaction",
            "WebTransaction/%s/%s" % (group, name),
            "WebTransactionTotalTime",
            "WebTransactionTotalTime/%s/%s" % (group, name),
            "HttpDispatcher",
        ]
        transaction_scope_name = "WebTransaction/%s/%s" % (group, name)

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_transaction_called = []
        recorded_metrics = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        @catch_background_exceptions
        def _validate_transaction_metrics(wrapped, instance, args, kwargs):
            record_transaction_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                metrics = instance.stats_table
                # Record a copy of the metric value so that the values aren't
                # merged in the future
                _metrics = {}
                for k, v in metrics.items():
                    _metrics[k] = copy.copy(v)
                recorded_metrics.append(_metrics)

            return result

        def _validate(metrics, name, scope, count):
            key = (name, scope)
            metric = metrics.get(key)

            def _metrics_table():
                out = [""]
                out.append("Expected: {0}: {1}".format(key, count))
                for metric_key, metric_value in metrics.items():
                    out.append("{0}: {1}".format(metric_key, metric_value[0]))
                return "\n".join(out)

            def _metric_details():
                return "metric=%r, count=%r" % (key, metric.call_count)

            if count is not None:
                assert metric is not None, _metrics_table()
                if count == "present":
                    assert metric.call_count > 0, _metric_details()
                else:
                    assert metric.call_count == count, _metric_details()

                assert metric.total_call_time >= 0, (key, metric)
                assert metric.total_exclusive_call_time >= 0, (key, metric)
                assert metric.min_call_time >= 0, (key, metric)
                assert metric.sum_of_squares >= 0, (key, metric)

            else:
                assert metric is None, _metrics_table()

        _new_wrapper = _validate_transaction_metrics(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_transaction_called
        metrics = recorded_metrics[index]

        record_transaction_called[:] = []
        recorded_metrics[:] = []

        for unscoped_metric in unscoped_metrics:
            _validate(metrics, unscoped_metric, "", 1)

        for scoped_name, scoped_count in scoped_metrics:
            _validate(metrics, scoped_name, transaction_scope_name, scoped_count)

        for rollup_name, rollup_count in rollup_metrics:
            _validate(metrics, rollup_name, "", rollup_count)

        for custom_name, custom_count in custom_metrics:
            _validate(metrics, custom_name, "", custom_count)

        custom_metric_names = {name for name, _ in custom_metrics}
        for name, _ in metrics:
            if name not in custom_metric_names:
                assert not name.startswith("Supportability/api/"), name

        return val

    return _validate_wrapper


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


def validate_transaction_errors(errors=None, required_params=None, forgone_params=None):
    errors = errors or []
    required_params = required_params or []
    forgone_params = forgone_params or []
    captured_errors = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    @catch_background_exceptions
    def _capture_transaction_errors(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        captured = transaction.errors

        captured_errors.append(captured)

        return wrapped(*args, **kwargs)

    @function_wrapper
    def _validate_transaction_errors(wrapped, instance, args, kwargs):
        _new_wrapped = _capture_transaction_errors(wrapped)
        output = _new_wrapped(*args, **kwargs)

        expected = sorted(errors)

        if captured_errors:
            captured = captured_errors[0]
        else:
            captured = []

        if errors and isinstance(errors[0], (tuple, list)):
            compare_to = sorted([(e.type, e.message) for e in captured])
        else:
            compare_to = sorted([e.type for e in captured])

        assert expected == compare_to, "expected=%r, captured=%r, errors=%r" % (expected, compare_to, captured)

        for e in captured:
            assert e.span_id
            for name, value in required_params:
                assert name in e.custom_params, "name=%r, params=%r" % (name, e.custom_params)
                assert e.custom_params[name] == value, "name=%r, value=%r, params=%r" % (
                    name,
                    value,
                    e.custom_params,
                )

            for name, value in forgone_params:
                assert name not in e.custom_params, "name=%r, params=%r" % (name, e.custom_params)

        return output

    return _validate_transaction_errors


def validate_transaction_event_attributes(required_params=None, forgone_params=None, exact_attrs=None, index=-1):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    captured_events = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _capture_transaction_events(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            event_data = instance.transaction_events
            captured_events.append(event_data)
            return result

    @function_wrapper
    def _validate_transaction_event_attributes(wrapped, instance, args, kwargs):
        _new_wrapper = _capture_transaction_events(wrapped)
        result = _new_wrapper(*args, **kwargs)

        assert captured_events, "No events captured"
        event_data = captured_events[index]
        captured_events[:] = []

        check_event_attributes(event_data, required_params, forgone_params, exact_attrs)

        return result

    return _validate_transaction_event_attributes


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


def validate_tt_collector_json(
    required_params=None,
    forgone_params=None,
    should_exist=True,
    datastore_params=None,
    datastore_forgone_params=None,
    message_broker_params=None,
    message_broker_forgone_params=None,
    exclude_request_uri=False,
):
    """make assertions based off the cross-agent spec on transaction traces"""
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    datastore_params = datastore_params or {}
    datastore_forgone_params = datastore_forgone_params or {}
    message_broker_params = message_broker_params or {}
    message_broker_forgone_params = message_broker_forgone_params or []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        traces_recorded = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        def _validate_tt_collector_json(wrapped, instance, args, kwargs):

            result = wrapped(*args, **kwargs)

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)
            traces_recorded.append(trace_data)

            return result

        def _validate_trace(trace):
            assert isinstance(trace[0], float)  # absolute start time (ms)
            assert isinstance(trace[1], float)  # duration (ms)
            assert trace[0] > 0  # absolute time (ms)
            assert isinstance(trace[2], six.string_types)  # transaction name
            if trace[2].startswith("WebTransaction"):
                if exclude_request_uri:
                    assert trace[3] is None  # request url
                else:
                    assert isinstance(trace[3], six.string_types)
                    # query parameters should not be captured
                    assert "?" not in trace[3]

            # trace details -- python agent always uses condensed trace array

            trace_details, string_table = unpack_field(trace[4])
            assert len(trace_details) == 5
            assert isinstance(trace_details[0], float)  # start time (ms)

            # the next two items should be empty dicts, old parameters stuff,
            # placeholders for now

            assert isinstance(trace_details[1], dict)
            assert len(trace_details[1]) == 0
            assert isinstance(trace_details[2], dict)
            assert len(trace_details[2]) == 0

            # root node in slot 3

            root_node = trace_details[3]
            assert isinstance(root_node[0], float)  # entry timestamp
            assert isinstance(root_node[1], float)  # exit timestamp
            assert root_node[2] == "ROOT"
            assert isinstance(root_node[3], dict)
            assert len(root_node[3]) == 0  # spec shows empty (for root)
            children = root_node[4]
            assert isinstance(children, list)

            # there are two optional items at the end of trace segments,
            # class name that segment is in, and method name function is in;
            # Python agent does not use these (only Java does)

            # let's just test the first child
            trace_segment = children[0]
            assert isinstance(trace_segment[0], float)  # entry timestamp
            assert isinstance(trace_segment[1], float)  # exit timestamp
            assert isinstance(trace_segment[2], six.string_types)  # scope
            assert isinstance(trace_segment[3], dict)  # request params
            assert isinstance(trace_segment[4], list)  # children

            assert trace_segment[0] >= root_node[0]  # trace starts after root

            def _check_params_and_start_time(node):
                children = node[4]
                for child in children:
                    assert child[0] >= node[0]  # child started after parent
                    _check_params_and_start_time(child)

                params = node[3]
                assert isinstance(params, dict)

                # We should always report exclusive_duration_millis on a
                # segment. This allows us to override exclusive time
                # calculations on APM.
                assert "exclusive_duration_millis" in params
                assert isinstance(params["exclusive_duration_millis"], float)

                segment_name = _lookup_string_table(node[2], string_table, default=node[2])
                if segment_name.startswith("Datastore"):
                    for key in datastore_params:
                        assert key in params, key
                        assert params[key] == datastore_params[key]
                    for key in datastore_forgone_params:
                        assert key not in params, key

                    # if host is reported, it cannot be localhost
                    if "host" in params:
                        assert params["host"] not in LOCALHOST_EQUIVALENTS

                elif segment_name.startswith("MessageBroker"):
                    for key in message_broker_params:
                        assert key in params, key
                        assert params[key] == message_broker_params[key]
                    for key in message_broker_forgone_params:
                        assert key not in params, key

            _check_params_and_start_time(trace_segment)

            attributes = trace_details[4]

            assert "intrinsics" in attributes
            assert "userAttributes" in attributes
            assert "agentAttributes" in attributes

            assert isinstance(trace[5], six.string_types)  # GUID
            assert trace[6] is None  # reserved for future use
            assert trace[7] is False  # deprecated force persist flag

            # x-ray session ID

            assert trace[8] is None

            # Synthetics ID

            assert trace[9] is None or isinstance(trace[9], six.string_types)

            assert isinstance(string_table, list)
            for name in string_table:
                assert isinstance(name, six.string_types)  # metric name

        _new_wrapper = _validate_tt_collector_json(wrapped)
        val = _new_wrapper(*args, **kwargs)
        trace_data = traces_recorded.pop()
        trace = trace_data[0]  # 1st trace
        _validate_trace(trace)
        return val

    return _validate_wrapper


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


def validate_tt_parameters(required_params=None, forgone_params=None):
    required_params = required_params or {}
    forgone_params = forgone_params or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_tt_parameters(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)
            pack_data = unpack_field(trace_data[0][4])
            tt_intrinsics = pack_data[0][4]["intrinsics"]

            for name in required_params:
                assert name in tt_intrinsics, "name=%r, intrinsics=%r" % (name, tt_intrinsics)
                assert tt_intrinsics[name] == required_params[name], "name=%r, value=%r, intrinsics=%r" % (
                    name,
                    required_params[name],
                    tt_intrinsics,
                )

            for name in forgone_params:
                assert name not in tt_intrinsics, "name=%r, intrinsics=%r" % (name, tt_intrinsics)

        return result

    return _validate_tt_parameters


def validate_tt_segment_params(forgone_params=(), present_params=(), exact_params=None):
    exact_params = exact_params or {}
    recorded_traces = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _extract_trace(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        # Now that transaction has been recorded, generate
        # a transaction trace

        connections = SQLConnections()
        trace_data = instance.transaction_trace_data(connections)
        # Save the recorded traces
        recorded_traces.extend(trace_data)

        return result

    @function_wrapper
    def validator(wrapped, instance, args, kwargs):
        new_wrapper = _extract_trace(wrapped)
        result = new_wrapper(*args, **kwargs)

        # Verify that traces have been recorded
        assert recorded_traces

        # Extract the first transaction trace
        transaction_trace = recorded_traces[0]
        pack_data = unpack_field(transaction_trace[4])

        # Extract the root segment from the root node
        root_segment = pack_data[0][3]

        recorded_params = {}

        def _validate_segment_params(segment):
            segment_params = segment[3]

            # Translate from the string cache
            for key, value in segment_params.items():
                if hasattr(value, "startswith") and value.startswith("`"):
                    try:
                        index = int(value[1:])
                        value = pack_data[1][index]
                    except ValueError:
                        pass
                segment_params[key] = value

            recorded_params.update(segment_params)

            for child_segment in segment[4]:
                _validate_segment_params(child_segment)

        _validate_segment_params(root_segment)

        recorded_params_set = set(recorded_params.keys())

        # Verify that the params in present params have been recorded
        present_params_set = set(present_params)
        assert recorded_params_set.issuperset(present_params_set)

        # Verify that all forgone params are omitted
        recorded_forgone_params = recorded_params_set & set(forgone_params)
        assert not recorded_forgone_params

        # Verify that all exact params are correct
        for key, value in exact_params.items():
            assert recorded_params[key] == value

        return result

    return validator


def validate_transaction_event_sample_data(required_attrs, required_user_attrs=True):
    """This test depends on values in the test application from
    agent_features/test_analytics.py, and is only meant to be run as a
    validation with those tests.
    """

    @transient_function_wrapper("newrelic.core.stats_engine", "SampledDataSet.add")
    def _validate_transaction_event_sample_data(wrapped, instance, args, kwargs):
        def _bind_params(sample, *args, **kwargs):
            return sample

        sample = _bind_params(*args, **kwargs)

        assert isinstance(sample, list)
        assert len(sample) == 3

        intrinsics, user_attributes, _ = sample

        assert intrinsics["type"] == "Transaction"
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

    return _validate_transaction_event_sample_data


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


def _validate_custom_event(recorded_event, required_event):
    assert len(recorded_event) == 2  # [intrinsic, user attributes]

    intrinsics = recorded_event[0]

    assert intrinsics["type"] == required_event[0]["type"]

    now = time.time()
    assert isinstance(intrinsics["timestamp"], int)
    assert intrinsics["timestamp"] <= 1000.0 * now
    assert intrinsics["timestamp"] >= 1000.0 * required_event[0]["timestamp"]

    assert recorded_event[1].items() == required_event[1].items()


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
        try:
            # The settings object has references from a number of
            # different places. We have to create a copy, overlay
            # the temporary settings and then when done clear the
            # top level settings object and rebuild it when done.

            original_settings = application_settings()
            backup = copy.deepcopy(original_settings.__dict__)
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
        try:
            # In some cases, a settings object may have references
            # from a number of different places. We have to create
            # a copy, overlay the temporary settings and then when
            # done, clear the top level settings object and rebuild
            # it when done.

            original = settings_object

            backup = copy.deepcopy(original.__dict__)
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
        try:
            # Updates can be made to ignored status codes in server
            # side configs. Changes will be applied to application
            # settings so we first check there and if they don't
            # exist, we default to global settings

            application = application_instance()
            settings = application and application.settings

            if not settings:
                settings = global_settings()

            original = settings.error_collector.ignore_status_codes
            settings.error_collector.ignore_status_codes = status_codes
            return wrapped(*args, **kwargs)
        finally:
            settings.error_collector.ignore_status_codes = original

    return _override_ignore_status_codes


def code_coverage_fixture(source=None):
    source = source if source is not None else ["newrelic"]

    @pytest.fixture(scope="session")
    def _code_coverage_fixture(request):
        if not source:
            return

        if os.environ.get("GITHUB_ACTIONS") is not None:
            return

        from coverage import coverage

        coverage_directory = os.environ.get("TOX_ENVDIR", "htmlcov")
        coverage_suffix = os.environ.get("TOX_ENV_NAME", None)

        def finalize():
            cov.stop()
            cov.html_report(directory=coverage_directory)

        request.addfinalizer(finalize)

        cov = coverage(source=source, branch=True, data_suffix=coverage_suffix)
        cov.start()

    return _code_coverage_fixture


def reset_core_stats_engine():
    @function_wrapper
    def _reset_core_stats_engine(wrapped, instance, args, kwargs):
        stats = core_application_stats_engine()
        stats.reset_stats(stats.settings)
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

        _samples = [s for s in samples if s[0]["type"] == "Transaction"]
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
