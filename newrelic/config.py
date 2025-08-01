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

import configparser
import fnmatch
import logging
import os
import sys
import threading
import time
import traceback
from pathlib import Path

import newrelic.api.application
import newrelic.api.background_task
import newrelic.api.database_trace
import newrelic.api.error_trace
import newrelic.api.exceptions
import newrelic.api.external_trace
import newrelic.api.function_profile
import newrelic.api.function_trace
import newrelic.api.generator_trace
import newrelic.api.import_hook
import newrelic.api.memcache_trace
import newrelic.api.profile_trace
import newrelic.api.settings
import newrelic.api.transaction_name
import newrelic.api.wsgi_application
import newrelic.console
import newrelic.core.agent
import newrelic.core.config
from newrelic.common.log_file import initialize_logging
from newrelic.common.object_names import callable_name, expand_builtin_exception_name
from newrelic.core import trace_cache
from newrelic.core.agent_control_health import (
    HealthStatus,
    agent_control_health_instance,
    agent_control_healthcheck_loop,
)
from newrelic.core.config import Settings, apply_config_setting, default_host, fetch_config_setting

__all__ = ["initialize", "filter_app_factory"]

_logger = logging.getLogger(__name__)


def _map_aws_account_id(s):
    return newrelic.core.config._map_aws_account_id(s, _logger)


# Register our importer which implements post import hooks for
# triggering of callbacks to monkey patch modules before import
# returns them to caller.

sys.meta_path.insert(0, newrelic.api.import_hook.ImportHookFinder())

# The set of valid feature flags that the agent currently uses.
# This will be used to validate what is provided and issue warnings
# if feature flags not in set are provided.

_FEATURE_FLAGS = {"django.instrumentation.inclusion-tags.r1"}

# Names of configuration file and deployment environment. This
# will be overridden by the load_configuration() function when
# configuration is loaded.

_config_file = None
_environment = None
_ignore_errors = True

# This is the actual internal settings object. Options which
# are read from the configuration file will be applied to this.

_settings = newrelic.api.settings.settings()

# Use the raw config parser as we want to avoid interpolation
# within values. This avoids problems when writing lambdas
# within the actual configuration file for options which value
# can be dynamically calculated at time wrapper is executed.
# This configuration object can be used by the instrumentation
# modules to look up customised settings defined in the loaded
# configuration file.

_config_object = configparser.RawConfigParser()

# Cache of the parsed global settings found in the configuration
# file. We cache these so can dump them out to the log file once
# all the settings have been read.

_cache_object = []
agent_control_health = agent_control_health_instance()


def _reset_config_parser():
    global _config_object
    global _cache_object
    _config_object = configparser.RawConfigParser()
    _cache_object = []


# Mechanism for extracting settings from the configuration for use in
# instrumentation modules and extensions.


def extra_settings(section, types=None, defaults=None):
    if types is None:
        types = {}
    if defaults is None:
        defaults = {}
    settings = {}

    if _config_object.has_section(section):
        settings.update(_config_object.items(section))

    settings_object = Settings()

    for name, value in defaults.items():
        apply_config_setting(settings_object, name, value)

    for name, value in settings.items():
        if name in types:
            value = types[name](value)

        apply_config_setting(settings_object, name, value)

    return settings_object


# Define some mapping functions to convert raw values read from
# configuration file into the internal types expected by the
# internal configuration settings object.

_LOG_LEVEL = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

_RECORD_SQL = {
    "off": newrelic.api.settings.RECORDSQL_OFF,
    "raw": newrelic.api.settings.RECORDSQL_RAW,
    "obfuscated": newrelic.api.settings.RECORDSQL_OBFUSCATED,
}

_COMPRESSED_CONTENT_ENCODING = {
    "deflate": newrelic.api.settings.COMPRESSED_CONTENT_ENCODING_DEFLATE,
    "gzip": newrelic.api.settings.COMPRESSED_CONTENT_ENCODING_GZIP,
}


def _map_log_level(s):
    return _LOG_LEVEL[s.upper()]


def _map_feature_flag(s):
    return set(s.split())


def _map_as_mapping(s):
    return newrelic.core.config._environ_as_mapping(name="", default=s)


def _map_transaction_threshold(s):
    if s == "apdex_f":
        return None
    return float(s)


def _map_record_sql(s):
    return _RECORD_SQL[s]


def _map_compressed_content_encoding(s):
    return _COMPRESSED_CONTENT_ENCODING[s]


def _map_split_strings(s):
    return s.split()


def _map_console_listener_socket(s):
    return s % {"pid": os.getpid()}


def _merge_ignore_status_codes(s):
    return newrelic.core.config._parse_status_codes(s, _settings.error_collector.ignore_status_codes)


def _merge_expected_status_codes(s):
    return newrelic.core.config._parse_status_codes(s, _settings.error_collector.expected_status_codes)


def _map_browser_monitoring_content_type(s):
    return s.split()


def _map_strip_exception_messages_allowlist(s):
    return [expand_builtin_exception_name(item) for item in s.split()]


def _map_inc_excl_attributes(s):
    return newrelic.core.config._parse_attributes(s)


def _map_case_insensitive_excl_labels(s):
    return [v.lower() for v in newrelic.core.config._parse_attributes(s)]


def _map_default_host_value(license_key):
    # If the license key is region aware, we should override the default host
    # to be the region aware host
    _default_host = default_host(license_key)
    _settings.host = os.environ.get("NEW_RELIC_HOST", _default_host)

    return license_key


# Processing of a single setting from configuration file.


def _raise_configuration_error(section, option=None):
    _logger.error("CONFIGURATION ERROR")
    if section:
        _logger.error("Section = %s", section)

    if option is None:
        options = _config_object.options(section)

        _logger.error("Options = %s", options)
        _logger.exception("Exception Details")

        if not _ignore_errors:
            if section:
                raise newrelic.api.exceptions.ConfigurationError(
                    f'Invalid configuration for section "{section}". Check New Relic agent log file for further details.'
                )
            raise newrelic.api.exceptions.ConfigurationError(
                "Invalid configuration. Check New Relic agent log file for further details."
            )

    else:
        _logger.error("Option = %s", option)
        _logger.exception("Exception Details")

        if not _ignore_errors:
            if section:
                raise newrelic.api.exceptions.ConfigurationError(
                    f'Invalid configuration for option "{option}" in section "{section}". Check New Relic agent log file for further details.'
                )
            raise newrelic.api.exceptions.ConfigurationError(
                f'Invalid configuration for option "{option}". Check New Relic agent log file for further details.'
            )


def _process_setting(section, option, getter, mapper):
    try:
        # The type of a value is dictated by the getter
        # function supplied.

        value = getattr(_config_object, getter)(section, option)

        # The getter parsed the value okay but want to
        # pass this through a mapping function to change
        # it to internal value suitable for internal
        # settings object. This is usually one where the
        # value was a string.

        if mapper:
            value = mapper(value)

        # Now need to apply the option from the
        # configuration file to the internal settings
        # object. Walk the object path and assign it.

        target = _settings
        fields = option.split(".", 1)

        while True:
            if len(fields) == 1:
                setattr(target, fields[0], value)
                break
            target = getattr(target, fields[0])
            fields = fields[1].split(".", 1)

        # Cache the configuration so can be dumped out to
        # log file when whole main configuration has been
        # processed. This ensures that the log file and log
        # level entries have been set.

        _cache_object.append((option, value))

    except configparser.NoSectionError:
        pass

    except configparser.NoOptionError:
        pass

    except Exception:
        _raise_configuration_error(section, option)


# Processing of all the settings for specified section except
# for log file and log level which are applied separately to
# ensure they are set as soon as possible.


def _process_configuration(section):
    _process_setting(section, "feature_flag", "get", _map_feature_flag)
    _process_setting(section, "app_name", "get", None)
    _process_setting(section, "labels", "get", _map_as_mapping)
    _process_setting(section, "license_key", "get", _map_default_host_value)
    _process_setting(section, "api_key", "get", None)
    _process_setting(section, "host", "get", None)
    _process_setting(section, "port", "getint", None)
    _process_setting(section, "otlp_host", "get", None)
    _process_setting(section, "otlp_port", "getint", None)
    _process_setting(section, "ssl", "getboolean", None)
    _process_setting(section, "proxy_scheme", "get", None)
    _process_setting(section, "proxy_host", "get", None)
    _process_setting(section, "proxy_port", "getint", None)
    _process_setting(section, "proxy_user", "get", None)
    _process_setting(section, "proxy_pass", "get", None)
    _process_setting(section, "ca_bundle_path", "get", None)
    _process_setting(section, "audit_log_file", "get", None)
    _process_setting(section, "monitor_mode", "getboolean", None)
    _process_setting(section, "developer_mode", "getboolean", None)
    _process_setting(section, "high_security", "getboolean", None)
    _process_setting(section, "capture_params", "getboolean", None)
    _process_setting(section, "ignored_params", "get", _map_split_strings)
    _process_setting(section, "capture_environ", "getboolean", None)
    _process_setting(section, "include_environ", "get", _map_split_strings)
    _process_setting(section, "max_stack_trace_lines", "getint", None)
    _process_setting(section, "startup_timeout", "getfloat", None)
    _process_setting(section, "shutdown_timeout", "getfloat", None)
    _process_setting(section, "compressed_content_encoding", "get", _map_compressed_content_encoding)
    _process_setting(section, "attributes.enabled", "getboolean", None)
    _process_setting(section, "attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "transaction_name.naming_scheme", "get", None)
    _process_setting(section, "gc_runtime_metrics.enabled", "getboolean", None)
    _process_setting(section, "gc_runtime_metrics.top_object_count_limit", "getint", None)
    _process_setting(section, "memory_runtime_pid_metrics.enabled", "getboolean", None)
    _process_setting(section, "thread_profiler.enabled", "getboolean", None)
    _process_setting(section, "transaction_tracer.enabled", "getboolean", None)
    _process_setting(section, "transaction_tracer.transaction_threshold", "get", _map_transaction_threshold)
    _process_setting(section, "transaction_tracer.record_sql", "get", _map_record_sql)
    _process_setting(section, "transaction_tracer.stack_trace_threshold", "getfloat", None)
    _process_setting(section, "transaction_tracer.explain_enabled", "getboolean", None)
    _process_setting(section, "transaction_tracer.explain_threshold", "getfloat", None)
    _process_setting(section, "transaction_tracer.function_trace", "get", _map_split_strings)
    _process_setting(section, "transaction_tracer.generator_trace", "get", _map_split_strings)
    _process_setting(section, "transaction_tracer.top_n", "getint", None)
    _process_setting(section, "transaction_tracer.attributes.enabled", "getboolean", None)
    _process_setting(section, "transaction_tracer.attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "transaction_tracer.attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "error_collector.enabled", "getboolean", None)
    _process_setting(section, "error_collector.capture_events", "getboolean", None)
    _process_setting(section, "error_collector.max_event_samples_stored", "getint", None)
    _process_setting(section, "error_collector.capture_source", "getboolean", None)
    _process_setting(section, "error_collector.ignore_errors", "get", _map_split_strings)
    _process_setting(section, "error_collector.ignore_classes", "get", _map_split_strings)
    _process_setting(section, "error_collector.ignore_status_codes", "get", _merge_ignore_status_codes)
    _process_setting(section, "error_collector.expected_classes", "get", _map_split_strings)
    _process_setting(section, "error_collector.expected_status_codes", "get", _merge_expected_status_codes)
    _process_setting(section, "error_collector.attributes.enabled", "getboolean", None)
    _process_setting(section, "error_collector.attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "error_collector.attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "browser_monitoring.enabled", "getboolean", None)
    _process_setting(section, "browser_monitoring.auto_instrument", "getboolean", None)
    _process_setting(section, "browser_monitoring.loader", "get", None)
    _process_setting(section, "browser_monitoring.debug", "getboolean", None)
    _process_setting(section, "browser_monitoring.ssl_for_http", "getboolean", None)
    _process_setting(section, "browser_monitoring.content_type", "get", _map_split_strings)
    _process_setting(section, "browser_monitoring.attributes.enabled", "getboolean", None)
    _process_setting(section, "browser_monitoring.attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "browser_monitoring.attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "slow_sql.enabled", "getboolean", None)
    _process_setting(section, "synthetics.enabled", "getboolean", None)
    _process_setting(section, "transaction_events.enabled", "getboolean", None)
    _process_setting(section, "transaction_events.max_samples_stored", "getint", None)
    _process_setting(section, "transaction_events.attributes.enabled", "getboolean", None)
    _process_setting(section, "transaction_events.attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "transaction_events.attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "custom_insights_events.enabled", "getboolean", None)
    _process_setting(section, "custom_insights_events.max_samples_stored", "getint", None)
    _process_setting(section, "custom_insights_events.max_attribute_value", "getint", None)
    _process_setting(section, "ml_insights_events.enabled", "getboolean", None)
    _process_setting(section, "distributed_tracing.enabled", "getboolean", None)
    _process_setting(section, "distributed_tracing.exclude_newrelic_header", "getboolean", None)
    _process_setting(section, "span_events.enabled", "getboolean", None)
    _process_setting(section, "span_events.max_samples_stored", "getint", None)
    _process_setting(section, "span_events.attributes.enabled", "getboolean", None)
    _process_setting(section, "span_events.attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "span_events.attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "transaction_segments.attributes.enabled", "getboolean", None)
    _process_setting(section, "transaction_segments.attributes.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "transaction_segments.attributes.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "local_daemon.socket_path", "get", None)
    _process_setting(section, "local_daemon.synchronous_startup", "getboolean", None)
    _process_setting(section, "agent_limits.transaction_traces_nodes", "getint", None)
    _process_setting(section, "agent_limits.sql_query_length_maximum", "getint", None)
    _process_setting(section, "agent_limits.slow_sql_stack_trace", "getint", None)
    _process_setting(section, "agent_limits.max_sql_connections", "getint", None)
    _process_setting(section, "agent_limits.sql_explain_plans", "getint", None)
    _process_setting(section, "agent_limits.sql_explain_plans_per_harvest", "getint", None)
    _process_setting(section, "agent_limits.slow_sql_data", "getint", None)
    _process_setting(section, "agent_limits.merge_stats_maximum", "getint", None)
    _process_setting(section, "agent_limits.errors_per_transaction", "getint", None)
    _process_setting(section, "agent_limits.errors_per_harvest", "getint", None)
    _process_setting(section, "agent_limits.slow_transaction_dry_harvests", "getint", None)
    _process_setting(section, "agent_limits.thread_profiler_nodes", "getint", None)
    _process_setting(section, "agent_limits.synthetics_events", "getint", None)
    _process_setting(section, "agent_limits.synthetics_transactions", "getint", None)
    _process_setting(section, "agent_limits.data_compression_threshold", "getint", None)
    _process_setting(section, "agent_limits.data_compression_level", "getint", None)
    _process_setting(section, "console.listener_socket", "get", _map_console_listener_socket)
    _process_setting(section, "console.allow_interpreter_cmd", "getboolean", None)
    _process_setting(section, "debug.disable_api_supportability_metrics", "getboolean", None)
    _process_setting(section, "debug.log_data_collector_calls", "getboolean", None)
    _process_setting(section, "debug.log_data_collector_payloads", "getboolean", None)
    _process_setting(section, "debug.log_malformed_json_data", "getboolean", None)
    _process_setting(section, "debug.log_transaction_trace_payload", "getboolean", None)
    _process_setting(section, "debug.log_thread_profile_payload", "getboolean", None)
    _process_setting(section, "debug.log_raw_metric_data", "getboolean", None)
    _process_setting(section, "debug.log_normalized_metric_data", "getboolean", None)
    _process_setting(section, "debug.log_normalization_rules", "getboolean", None)
    _process_setting(section, "debug.log_agent_initialization", "getboolean", None)
    _process_setting(section, "debug.log_explain_plan_queries", "getboolean", None)
    _process_setting(section, "debug.log_autorum_middleware", "getboolean", None)
    _process_setting(section, "debug.log_untrusted_distributed_trace_keys", "getboolean", None)
    _process_setting(section, "debug.enable_coroutine_profiling", "getboolean", None)
    _process_setting(section, "debug.record_transaction_failure", "getboolean", None)
    _process_setting(section, "debug.explain_plan_obfuscation", "get", None)
    _process_setting(section, "debug.disable_certificate_validation", "getboolean", None)
    _process_setting(section, "debug.disable_harvest_until_shutdown", "getboolean", None)
    _process_setting(section, "debug.connect_span_stream_in_developer_mode", "getboolean", None)
    _process_setting(section, "debug.otlp_content_encoding", "get", None)
    _process_setting(section, "cross_application_tracer.enabled", "getboolean", None)
    _process_setting(section, "message_tracer.segment_parameters_enabled", "getboolean", None)
    _process_setting(section, "process_host.display_name", "get", None)
    _process_setting(section, "utilization.detect_aws", "getboolean", None)
    _process_setting(section, "utilization.detect_azure", "getboolean", None)
    _process_setting(section, "utilization.detect_azurefunction", "getboolean", None)
    _process_setting(section, "utilization.detect_docker", "getboolean", None)
    _process_setting(section, "utilization.detect_kubernetes", "getboolean", None)
    _process_setting(section, "utilization.detect_gcp", "getboolean", None)
    _process_setting(section, "utilization.detect_pcf", "getboolean", None)
    _process_setting(section, "utilization.logical_processors", "getint", None)
    _process_setting(section, "utilization.total_ram_mib", "getint", None)
    _process_setting(section, "utilization.billing_hostname", "get", None)
    _process_setting(section, "strip_exception_messages.enabled", "getboolean", None)
    _process_setting(section, "strip_exception_messages.allowlist", "get", _map_strip_exception_messages_allowlist)
    _process_setting(section, "datastore_tracer.instance_reporting.enabled", "getboolean", None)
    _process_setting(section, "datastore_tracer.database_name_reporting.enabled", "getboolean", None)
    _process_setting(section, "heroku.use_dyno_names", "getboolean", None)
    _process_setting(section, "heroku.dyno_name_prefixes_to_shorten", "get", _map_split_strings)
    _process_setting(section, "serverless_mode.enabled", "getboolean", None)
    _process_setting(section, "apdex_t", "getfloat", None)
    _process_setting(section, "event_loop_visibility.enabled", "getboolean", None)
    _process_setting(section, "event_loop_visibility.blocking_threshold", "getfloat", None)
    _process_setting(section, "event_harvest_config.harvest_limits.analytic_event_data", "getint", None)
    _process_setting(section, "event_harvest_config.harvest_limits.custom_event_data", "getint", None)
    _process_setting(section, "event_harvest_config.harvest_limits.ml_event_data", "getint", None)
    _process_setting(section, "event_harvest_config.harvest_limits.span_event_data", "getint", None)
    _process_setting(section, "event_harvest_config.harvest_limits.error_event_data", "getint", None)
    _process_setting(section, "event_harvest_config.harvest_limits.log_event_data", "getint", None)
    _process_setting(section, "infinite_tracing.trace_observer_host", "get", None)
    _process_setting(section, "infinite_tracing.trace_observer_port", "getint", None)
    _process_setting(section, "infinite_tracing.compression", "getboolean", None)
    _process_setting(section, "infinite_tracing.batching", "getboolean", None)
    _process_setting(section, "infinite_tracing.span_queue_size", "getint", None)
    _process_setting(section, "code_level_metrics.enabled", "getboolean", None)

    _process_setting(section, "application_logging.enabled", "getboolean", None)
    _process_setting(section, "application_logging.forwarding.max_samples_stored", "getint", None)
    _process_setting(section, "application_logging.forwarding.enabled", "getboolean", None)
    _process_setting(section, "application_logging.forwarding.custom_attributes", "get", _map_as_mapping)
    _process_setting(section, "application_logging.forwarding.labels.enabled", "getboolean", None)
    _process_setting(section, "application_logging.forwarding.labels.exclude", "get", _map_case_insensitive_excl_labels)
    _process_setting(section, "application_logging.forwarding.context_data.enabled", "getboolean", None)
    _process_setting(section, "application_logging.forwarding.context_data.include", "get", _map_inc_excl_attributes)
    _process_setting(section, "application_logging.forwarding.context_data.exclude", "get", _map_inc_excl_attributes)
    _process_setting(section, "application_logging.metrics.enabled", "getboolean", None)
    _process_setting(section, "application_logging.local_decorating.enabled", "getboolean", None)

    _process_setting(section, "machine_learning.enabled", "getboolean", None)
    _process_setting(section, "machine_learning.inference_events_value.enabled", "getboolean", None)
    _process_setting(section, "ai_monitoring.enabled", "getboolean", None)
    _process_setting(section, "ai_monitoring.record_content.enabled", "getboolean", None)
    _process_setting(section, "ai_monitoring.streaming.enabled", "getboolean", None)
    _process_setting(section, "cloud.aws.account_id", "get", _map_aws_account_id)
    _process_setting(section, "k8s_operator.enabled", "getboolean", None)
    _process_setting(section, "azure_operator.enabled", "getboolean", None)
    _process_setting(section, "package_reporting.enabled", "getboolean", None)
    _process_setting(section, "instrumentation.graphql.capture_introspection_queries", "getboolean", None)
    _process_setting(
        section, "instrumentation.kombu.ignored_exchanges", "get", newrelic.core.config.parse_space_separated_into_list
    )
    _process_setting(section, "instrumentation.kombu.consumer.enabled", "getboolean", None)


# Loading of configuration from specified file and for specified
# deployment environment. Can also indicate whether configuration
# and instrumentation errors should raise an exception or not.

_configuration_done = False


def _reset_configuration_done():
    global _configuration_done
    _configuration_done = False


def _process_app_name_setting():
    # Do special processing to handle the case where the application
    # name was actually a semicolon separated list of names. In this
    # case the first application name is the primary and the others are
    # linked applications the application also reports to. What we need
    # to do is explicitly retrieve the application object for the
    # primary application name and link it with the other applications.
    # When activating the application the linked names will be sent
    # along to the core application where the association will be
    # created if it does not exist.

    app_name_list = _settings.app_name.split(";")
    name = app_name_list[0].strip() or "Python Application"

    if len(app_name_list) > 3:
        agent_control_health.set_health_status(HealthStatus.MAX_APP_NAME.value)

    linked = []
    for altname in app_name_list[1:]:
        altname = altname.strip()
        if altname:
            linked.append(altname)

    def _link_applications(application):
        for altname in linked:
            _logger.debug("link to %s", ((name, altname),))
            application.link_to_application(altname)

    if linked:
        newrelic.api.application.Application.run_on_initialization(name, _link_applications)
        _settings.linked_applications = linked

    _settings.app_name = name


def _process_labels_setting(labels=None):
    # Do special processing to handle labels. Initially the labels
    # setting will be a list of key/value tuples. This needs to be
    # converted into a list of dictionaries. It is also necessary
    # to eliminate duplicates by taking the last value, plus apply
    # length limits and limits on the number collected.

    if labels is None:
        labels = _settings.labels

    length_limit = 255
    count_limit = 64

    deduped = {}

    for key, value in labels:
        if len(key) > length_limit:
            _logger.warning(
                "Improper configuration. Label key %s is too long. Truncating key to: %s", key, key[:length_limit]
            )

        if len(value) > length_limit:
            _logger.warning(
                "Improper configuration. Label value %s is too long. Truncating value to: %s",
                value,
                value[:length_limit],
            )

        if len(deduped) >= count_limit:
            _logger.warning(
                "Improper configuration. Maximum number of labels reached. Using first %d labels.", count_limit
            )
            break

        key = key[:length_limit]
        value = value[:length_limit]

        deduped[key] = value

    result = []

    for key, value in deduped.items():
        result.append({"label_type": key, "label_value": value})

    _settings.labels = result


def delete_setting(settings_object, name):
    """Delete setting from settings_object.

    If passed a 'root' setting, like 'error_collector', it will
    delete 'error_collector' and all settings underneath it, such
    as 'error_collector.attributes.enabled'

    """

    target = settings_object
    fields = name.split(".", 1)

    while len(fields) > 1:
        if not hasattr(target, fields[0]):
            break
        target = getattr(target, fields[0])
        fields = fields[1].split(".", 1)

    try:
        delattr(target, fields[0])
    except AttributeError:
        _logger.debug("Failed to delete setting: %r", name)


def translate_deprecated_settings(settings, cached_settings):
    # If deprecated setting has been set by user, but the new
    # setting has not, then translate the deprecated setting to the
    # new one.
    #
    # If both deprecated and new setting have been applied, ignore
    # deprecated setting.
    #
    # In either case, delete the deprecated one from the settings object.

    # Parameters:
    #
    #    settings:
    #         Settings object
    #
    #   cached_settings:
    #         A list of (key, value) pairs of the parsed global settings
    #         found in the config file.

    # NOTE:
    #
    # cached_settings is a list of option key/values and can have duplicate
    # keys, if the customer used environment sections in the config file.
    # Since options are applied to the settings object in order, so that the
    # options at the end of the list will override earlier options with the
    # same key, then converting to a dict will result in each option having
    # the most recently applied value.

    cached = dict(cached_settings)

    deprecated_settings_map = [
        ("transaction_tracer.capture_attributes", "transaction_tracer.attributes.enabled"),
        ("error_collector.capture_attributes", "error_collector.attributes.enabled"),
        ("browser_monitoring.capture_attributes", "browser_monitoring.attributes.enabled"),
        ("analytics_events.capture_attributes", "transaction_events.attributes.enabled"),
        ("analytics_events.enabled", "transaction_events.enabled"),
        ("analytics_events.max_samples_stored", "event_harvest_config.harvest_limits.analytic_event_data"),
        ("transaction_events.max_samples_stored", "event_harvest_config.harvest_limits.analytic_event_data"),
        ("span_events.max_samples_stored", "event_harvest_config.harvest_limits.span_event_data"),
        ("error_collector.max_event_samples_stored", "event_harvest_config.harvest_limits.error_event_data"),
        ("custom_insights_events.max_samples_stored", "event_harvest_config.harvest_limits.custom_event_data"),
        ("application_logging.forwarding.max_samples_stored", "event_harvest_config.harvest_limits.log_event_data"),
        ("error_collector.ignore_errors", "error_collector.ignore_classes"),
        ("strip_exception_messages.whitelist", "strip_exception_messages.allowlist"),
    ]

    for old_key, new_key in deprecated_settings_map:
        if old_key in cached:
            _logger.info("Deprecated setting found: %r. Please use new setting: %r.", old_key, new_key)

            if new_key in cached:
                _logger.info("Ignoring deprecated setting: %r. Using new setting: %r.", old_key, new_key)
            else:
                apply_config_setting(settings, new_key, cached[old_key])
                _logger.info("Applying value of deprecated setting %r to %r.", old_key, new_key)

            delete_setting(settings, old_key)

    # The 'ignored_params' setting is more complicated than the above
    # deprecated settings, so it gets handled separately.

    if "ignored_params" in cached:
        _logger.info(
            "Deprecated setting found: ignored_params. Please use "
            "new setting: attributes.exclude. For the new setting, an "
            "ignored parameter should be prefaced with "
            '"request.parameters.". For example, ignoring a parameter '
            'named "foo" should be added added to attributes.exclude as '
            '"request.parameters.foo."'
        )

        # Don't merge 'ignored_params' settings. If user set
        # 'attributes.exclude' setting, only use those values,
        # and ignore 'ignored_params' settings.

        if "attributes.exclude" in cached:
            _logger.info("Ignoring deprecated setting: ignored_params. Using new setting: attributes.exclude.")

        else:
            ignored_params = fetch_config_setting(settings, "ignored_params")

            for p in ignored_params:
                attr_value = f"request.parameters.{p}"
                excluded_attrs = fetch_config_setting(settings, "attributes.exclude")

                if attr_value not in excluded_attrs:
                    settings.attributes.exclude.append(attr_value)
                    _logger.info(
                        "Applying value of deprecated setting ignored_params to attributes.exclude: %r.", attr_value
                    )

        delete_setting(settings, "ignored_params")

    # The 'capture_params' setting is deprecated, but since it affects
    # attribute filter default destinations, it is not translated here. We
    # log a message, but keep the capture_params setting.
    #
    # See newrelic.core.transaction:Transaction.agent_attributes to see how
    # it is used.

    if "capture_params" in cached:
        _logger.info(
            "Deprecated setting found: capture_params. Please use "
            "new setting: attributes.exclude. To disable capturing all "
            'request parameters, add "request.parameters.*" to '
            "attributes.exclude."
        )

    if "cross_application_tracer.enabled" in cached:
        # CAT Deprecation Warning
        _logger.info(
            "Deprecated setting found: cross_application_tracer.enabled. Please replace Cross Application Tracing "
            "(CAT) with the newer Distributed Tracing by setting 'distributed_tracing.enabled' to True in your agent "
            "configuration. For further details on distributed tracing, please refer to our documentation: "
            "https://docs.newrelic.com/docs/distributed-tracing/concepts/distributed-tracing-planning-guide/#changes."
        )

    if not settings.ssl:
        settings.ssl = True
        _logger.info("Ignoring deprecated setting: ssl. Enabling ssl is now mandatory. Setting ssl=true.")

    if settings.agent_limits.merge_stats_maximum is not None:
        _logger.info(
            "Ignoring deprecated setting: "
            "agent_limits.merge_stats_maximum. The agent will now respect "
            "server-side commands."
        )

    return settings


def apply_local_high_security_mode_setting(settings):
    # When High Security Mode is activated, certain settings must be
    # set to be secure, even if that requires overriding a setting that
    # has been individually configured as insecure.

    if not settings.high_security:
        return settings

    log_template = (
        "Overriding setting for %r because High "
        "Security Mode has been activated. The original "
        "setting was %r. The new setting is %r."
    )

    # capture_params is a deprecated setting for users, and has three
    # possible values:
    #
    #   True:  For backward compatibility.
    #   False: For backward compatibility.
    #   None:  The current default setting.
    #
    # In High Security, capture_params must be False, but we only need
    # to log if the customer has actually used the deprecated setting
    # and set it to True.

    if settings.capture_params:
        settings.capture_params = False
        _logger.info(log_template, "capture_params", True, False)
    elif settings.capture_params is None:
        settings.capture_params = False

    if settings.transaction_tracer.record_sql == "raw":
        settings.transaction_tracer.record_sql = "obfuscated"
        _logger.info(log_template, "transaction_tracer.record_sql", "raw", "obfuscated")

    if not settings.strip_exception_messages.enabled:
        settings.strip_exception_messages.enabled = True
        _logger.info(log_template, "strip_exception_messages.enabled", False, True)

    if settings.custom_insights_events.enabled:
        settings.custom_insights_events.enabled = False
        _logger.info(log_template, "custom_insights_events.enabled", True, False)

    if settings.ml_insights_events.enabled:
        settings.ml_insights_events.enabled = False
        _logger.info(log_template, "ml_insights_events.enabled", True, False)

    if settings.message_tracer.segment_parameters_enabled:
        settings.message_tracer.segment_parameters_enabled = False
        _logger.info(log_template, "message_tracer.segment_parameters_enabled", True, False)

    if settings.application_logging.forwarding.enabled:
        settings.application_logging.forwarding.enabled = False
        _logger.info(log_template, "application_logging.forwarding.enabled", True, False)

    if settings.machine_learning.inference_events_value.enabled:
        settings.machine_learning.inference_events_value.enabled = False
        _logger.info(log_template, "machine_learning.inference_events_value.enabled", True, False)

    if settings.ai_monitoring.enabled:
        settings.ai_monitoring.enabled = False
        _logger.info(log_template, "ai_monitoring.enabled", True, False)

    return settings


def _toml_config_to_configparser_dict(d, top=None, _path=None):
    top = top or {"newrelic": {}}
    _path = _path or ""
    for key, value in d.items():
        if isinstance(value, dict):
            _toml_config_to_configparser_dict(value, top, f"{_path}.{key}" if _path else key)
        else:
            fixed_value = " ".join(value) if isinstance(value, list) else value
            path_split = _path.split(".")
            # Handle environments
            if _path.startswith("env."):
                env_key = f"newrelic:{path_split[1]}"
                fixed_key = ".".join((*path_split[2:], key))
                top[env_key] = {**top.get(env_key, {}), fixed_key: fixed_value}
            # Handle import-hook:... configuration
            elif _path.startswith("import-hook."):
                import_hook_key = f"import-hook:{'.'.join(path_split[1:])}"
                top[import_hook_key] = {**top.get(import_hook_key, {}), key: fixed_value}
            else:
                top["newrelic"][f"{_path}.{key}" if _path else key] = fixed_value
    return top


def _load_configuration(config_file=None, environment=None, ignore_errors=True, log_file=None, log_level=None):
    global _configuration_done

    global _config_file
    global _environment
    global _ignore_errors

    # Check whether initialisation has been done previously. If
    # it has then raise a configuration error if it was against
    # a different configuration. Otherwise just return. We don't
    # check at this time if an incompatible configuration has
    # been read from a different sub interpreter. If this occurs
    # then results will be undefined. Use from different sub
    # interpreters of the same process is not recommended.

    if _configuration_done:
        if _config_file != config_file or _environment != environment:
            raise newrelic.api.exceptions.ConfigurationError(
                f'Configuration has already been done against differing configuration file or environment. Prior configuration file used was "{_config_file}" and environment "{_environment}".'
            )
        return

    _configuration_done = True

    # Normalize configuration file into a string path
    config_file = os.fsdecode(config_file) if config_file is not None else config_file

    # Update global variables tracking what configuration file and
    # environment was used, plus whether errors are to be ignored.

    _config_file = config_file
    _environment = environment
    _ignore_errors = ignore_errors

    # If no configuration file then nothing more to be done.

    if not config_file:
        _logger.debug("no agent configuration file")

        # Force initialisation of the logging system now in case
        # setup provided by environment variables.

        if log_file is None:
            log_file = _settings.log_file

        if log_level is None:
            log_level = _settings.log_level

        initialize_logging(log_file, log_level)

        # Validate provided feature flags and log a warning if get one
        # which isn't valid.

        for flag in _settings.feature_flag:
            if flag not in _FEATURE_FLAGS:
                _logger.warning(
                    "Unknown agent feature flag %r provided. "
                    "Check agent documentation or release notes, or "
                    "contact New Relic support for clarification of "
                    "validity of the specific feature flag.",
                    flag,
                )

        # Look for an app_name setting which is actually a semi colon
        # list of application names and adjust app_name setting and
        # registered linked applications for later handling.

        _process_app_name_setting()

        # Look for any labels and translate them into required form
        # for sending up to data collector on registration.

        _process_labels_setting()

        return

    _logger.debug("agent configuration file was %s", config_file)

    # Now read in the configuration file. Cache the config file
    # name in internal settings object as indication of succeeding.
    try:
        if config_file.endswith(".toml"):
            try:
                import tomllib
            except ImportError as exc:
                raise newrelic.api.exceptions.ConfigurationError(
                    "TOML configuration file can only be used if tomllib is available (Python 3.11+)."
                ) from exc
            with Path(config_file).open("rb") as f:
                content = tomllib.load(f)
                newrelic_section = content.get("tool", {}).get("newrelic")
                if not newrelic_section:
                    raise newrelic.api.exceptions.ConfigurationError("New Relic configuration not found in TOML file.")
                _config_object.read_dict(_toml_config_to_configparser_dict(newrelic_section))
        elif not _config_object.read([config_file]):
            raise newrelic.api.exceptions.ConfigurationError(f"Unable to open configuration file {config_file}.")
    except Exception:
        agent_control_health.set_health_status(HealthStatus.INVALID_CONFIG.value)
        raise

    _settings.config_file = config_file

    # Must process log file entries first so that errors with
    # the remainder will get logged if log file is defined.

    _process_setting("newrelic", "log_file", "get", None)

    if environment:
        _process_setting(f"newrelic:{environment}", "log_file", "get", None)

    if log_file is None:
        log_file = _settings.log_file

    _process_setting("newrelic", "log_level", "get", _map_log_level)

    if environment:
        _process_setting(f"newrelic:{environment}", "log_level", "get", _map_log_level)

    if log_level is None:
        log_level = _settings.log_level

    # Force initialisation of the logging system now that we
    # have the log file and log level.

    initialize_logging(log_file, log_level)

    # Now process the remainder of the global configuration
    # settings.

    _process_configuration("newrelic")

    # And any overrides specified with a section corresponding
    # to a specific deployment environment.

    if environment:
        _settings.environment = environment
        _process_configuration(f"newrelic:{environment}")

    # Log details of the configuration options which were
    # read and the values they have as would be applied
    # against the internal settings object.

    for option, value in _cache_object:
        _logger.debug("agent config %s = %s", option, repr(value))

    # Validate provided feature flags and log a warning if get one
    # which isn't valid.

    for flag in _settings.feature_flag:
        if flag not in _FEATURE_FLAGS:
            _logger.warning(
                "Unknown agent feature flag %r provided. "
                "Check agent documentation or release notes, or "
                "contact New Relic support for clarification of "
                "validity of the specific feature flag.",
                flag,
            )

    # Translate old settings

    translate_deprecated_settings(_settings, _cache_object)

    # Apply High Security Mode policy if enabled in local agent
    # configuration file.

    apply_local_high_security_mode_setting(_settings)

    # Look for an app_name setting which is actually a semi colon
    # list of application names and adjust app_name setting and
    # registered linked applications for later handling.

    _process_app_name_setting()

    # Look for any labels and translate them into required form
    # for sending up to data collector on registration.

    _process_labels_setting()

    # Instrument with function trace any callables supplied by the
    # user in the configuration.

    for function in _settings.transaction_tracer.function_trace:
        try:
            (module, object_path) = function.split(":", 1)

            name = None
            group = "Function"
            label = None
            params = None
            terminal = False
            rollup = None

            _logger.debug("register function-trace %s", ((module, object_path, name, group),))

            hook = _function_trace_import_hook(object_path, name, group, label, params, terminal, rollup)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section=None, option="transaction_tracer.function_trace")

    # Instrument with generator trace any callables supplied by the
    # user in the configuration.

    for function in _settings.transaction_tracer.generator_trace:
        try:
            (module, object_path) = function.split(":", 1)

            name = None
            group = "Function"

            _logger.debug("register generator-trace %s", ((module, object_path, name, group),))

            hook = _generator_trace_import_hook(object_path, name, group)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section=None, option="transaction_tracer.generator_trace")


# Generic error reporting functions.


def _raise_instrumentation_error(instrumentation_type, locals_dict):
    _logger.error("INSTRUMENTATION ERROR")
    _logger.error("Type = %s", instrumentation_type)
    _logger.error("Locals = %s", locals_dict)
    _logger.exception("Exception Details")

    if not _ignore_errors:
        raise newrelic.api.exceptions.InstrumentationError(
            "Failure when instrumenting code. Check New Relic agent log file for further details."
        )


# Registration of module import hooks defined in configuration file.

_module_import_hook_results = {}
_module_import_hook_registry = {}


def module_import_hook_results():
    return _module_import_hook_results


def _module_import_hook(target, module, function):
    def _instrument(target):
        _logger.debug("instrument module %s", ((target, module, function),))

        try:
            instrumented = target._nr_instrumented
        except AttributeError:
            instrumented = target._nr_instrumented = set()

        if (module, function) in instrumented:
            _logger.debug("instrumentation already run %s", ((target, module, function),))
            return

        instrumented.add((module, function))

        try:
            getattr(newrelic.api.import_hook.import_module(module), function)(target)

            _module_import_hook_results[(target.__name__, module, function)] = ""

        except Exception:
            _module_import_hook_results[(target.__name__, module, function)] = traceback.format_exception(
                *sys.exc_info()
            )

            _raise_instrumentation_error("import-hook", locals())

    return _instrument


def _process_module_configuration():
    for section in _config_object.sections():
        if not section.startswith("import-hook:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            execute = _config_object.get(section, "execute")
            fields = execute.split(":", 1)
            module = fields[0]
            function = "instrument"
            if len(fields) != 1:
                function = fields[1]

            target = section.split(":", 1)[1]

            if target not in _module_import_hook_registry:
                _module_import_hook_registry[target] = (module, function)

                _logger.debug("register module %s", ((target, module, function),))

                hook = _module_import_hook(target, module, function)
                newrelic.api.import_hook.register_import_hook(target, hook)

                _module_import_hook_results.setdefault((target, module, function), None)

        except Exception:
            _raise_configuration_error(section)


def _module_function_glob(module, object_path):
    """Match functions and class methods in a module to file globbing syntax."""
    if not any(c in object_path for c in ("*", "?", "[")):  # Identify globbing patterns
        return (object_path,)  # Returned value must be iterable
    else:
        # Gather module functions
        try:
            available_functions = {k: v for k, v in module.__dict__.items() if callable(v) and not isinstance(v, type)}
        except Exception:
            # Default to empty dict if no functions available
            available_functions = {}

        # Gather module classes and methods
        try:
            available_classes = {k: v for k, v in module.__dict__.items() if isinstance(v, type)}
            for cls in available_classes:
                try:
                    # Skip adding individual class's methods on failure
                    available_functions.update(
                        {
                            f"{cls}.{k}": v
                            for k, v in available_classes.get(cls).__dict__.items()
                            if callable(v) and not isinstance(v, type)
                        }
                    )
                except Exception:
                    pass
        except Exception:
            # Skip adding all class methods on failure
            pass

        # Under the hood uses fnmatch, which uses os.path.normcase
        # On windows this would cause issues with case insensitivity,
        # but on all other operating systems there should be no issues.
        return fnmatch.filter(available_functions, object_path)


# Setup wsgi application wrapper defined in configuration file.


def _wsgi_application_import_hook(object_path, application):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap wsgi-application %s", (target, func, application))
                newrelic.api.wsgi_application.wrap_wsgi_application(target, func, application)
        except Exception:
            _raise_instrumentation_error("wsgi-application", locals())

    return _instrument


def _process_wsgi_application_configuration():
    for section in _config_object.sections():
        if not section.startswith("wsgi-application:"):
            continue
        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            application = None

            if _config_object.has_option(section, "application"):
                application = _config_object.get(section, "application")

            _logger.debug("register wsgi-application %s", ((module, object_path, application),))

            hook = _wsgi_application_import_hook(object_path, application)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup background task wrapper defined in configuration file.


def _background_task_import_hook(object_path, application, name, group):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap background-task %s", (target, func, application, name, group))
                newrelic.api.background_task.wrap_background_task(target, func, application, name, group)
        except Exception:
            _raise_instrumentation_error("background-task", locals())

    return _instrument


def _process_background_task_configuration():
    for section in _config_object.sections():
        if not section.startswith("background-task:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            application = None
            name = None
            group = "Function"

            if _config_object.has_option(section, "application"):
                application = _config_object.get(section, "application")
            if _config_object.has_option(section, "name"):
                name = _config_object.get(section, "name")
            if _config_object.has_option(section, "group"):
                group = _config_object.get(section, "group")

            if name and name.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                name = eval(name, callable_vars)  # noqa: S307

            _logger.debug("register background-task %s", ((module, object_path, application, name, group),))

            hook = _background_task_import_hook(object_path, application, name, group)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup database traces defined in configuration file.


def _database_trace_import_hook(object_path, sql):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap database-trace %s", (target, func, sql))
                newrelic.api.database_trace.wrap_database_trace(target, func, sql)
        except Exception:
            _raise_instrumentation_error("database-trace", locals())

    return _instrument


def _process_database_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("database-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            sql = _config_object.get(section, "sql")

            if sql.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                sql = eval(sql, callable_vars)  # noqa: S307

            _logger.debug("register database-trace %s", ((module, object_path, sql),))

            hook = _database_trace_import_hook(object_path, sql)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup external traces defined in configuration file.


def _external_trace_import_hook(object_path, library, url, method):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap external-trace %s", (target, func, library, url, method))
                newrelic.api.external_trace.wrap_external_trace(target, func, library, url, method)
        except Exception:
            _raise_instrumentation_error("external-trace", locals())

    return _instrument


def _process_external_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("external-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            method = None

            library = _config_object.get(section, "library")
            url = _config_object.get(section, "url")
            if _config_object.has_option(section, "method"):
                method = _config_object.get(section, "method")

            if url.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                url = eval(url, callable_vars)  # noqa: S307

            if method and method.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                method = eval(method, callable_vars)  # noqa: S307

            _logger.debug("register external-trace %s", ((module, object_path, library, url, method),))

            hook = _external_trace_import_hook(object_path, library, url, method)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup function traces defined in configuration file.


def _function_trace_import_hook(object_path, name, group, label, params, terminal, rollup):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap function-trace %s", (target, func, name, group, label, params, terminal, rollup))
                newrelic.api.function_trace.wrap_function_trace(
                    target, func, name, group, label, params, terminal, rollup
                )
        except Exception:
            _raise_instrumentation_error("function-trace", locals())

    return _instrument


def _process_function_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("function-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            name = None
            group = "Function"
            label = None
            params = None
            terminal = False
            rollup = None

            if _config_object.has_option(section, "name"):
                name = _config_object.get(section, "name")
            if _config_object.has_option(section, "group"):
                group = _config_object.get(section, "group")
            if _config_object.has_option(section, "label"):
                label = _config_object.get(section, "label")
            if _config_object.has_option(section, "terminal"):
                terminal = _config_object.getboolean(section, "terminal")
            if _config_object.has_option(section, "rollup"):
                rollup = _config_object.get(section, "rollup")

            if name and name.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                name = eval(name, callable_vars)  # noqa: S307

            _logger.debug(
                "register function-trace %s", ((module, object_path, name, group, label, params, terminal, rollup),)
            )

            hook = _function_trace_import_hook(object_path, name, group, label, params, terminal, rollup)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup generator traces defined in configuration file.


def _generator_trace_import_hook(object_path, name, group):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap generator-trace %s", (target, func, name, group))
                newrelic.api.generator_trace.wrap_generator_trace(target, func, name, group)
        except Exception:
            _raise_instrumentation_error("generator-trace", locals())

    return _instrument


def _process_generator_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("generator-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            name = None
            group = "Function"

            if _config_object.has_option(section, "name"):
                name = _config_object.get(section, "name")
            if _config_object.has_option(section, "group"):
                group = _config_object.get(section, "group")

            if name and name.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                name = eval(name, callable_vars)  # noqa: S307

            _logger.debug("register generator-trace %s", ((module, object_path, name, group),))

            hook = _generator_trace_import_hook(object_path, name, group)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup profile traces defined in configuration file.


def _profile_trace_import_hook(object_path, name, group, depth):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap profile-trace %s", (target, func, name, group, depth))
                newrelic.api.profile_trace.wrap_profile_trace(target, func, name, group, depth=depth)
        except Exception:
            _raise_instrumentation_error("profile-trace", locals())

    return _instrument


def _process_profile_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("profile-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            name = None
            group = "Function"
            depth = 3

            if _config_object.has_option(section, "name"):
                name = _config_object.get(section, "name")
            if _config_object.has_option(section, "group"):
                group = _config_object.get(section, "group")
            if _config_object.has_option(section, "depth"):
                depth = _config_object.get(section, "depth")

            if name and name.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                name = eval(name, callable_vars)  # noqa: S307

            _logger.debug("register profile-trace %s", ((module, object_path, name, group, depth),))

            hook = _profile_trace_import_hook(object_path, name, group, depth=depth)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup memcache traces defined in configuration file.


def _memcache_trace_import_hook(object_path, command):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap memcache-trace %s", (target, func, command))
                newrelic.api.memcache_trace.wrap_memcache_trace(target, func, command)
        except Exception:
            _raise_instrumentation_error("memcache-trace", locals())

    return _instrument


def _process_memcache_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("memcache-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            command = _config_object.get(section, "command")

            if command.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                command = eval(command, callable_vars)  # noqa: S307

            _logger.debug("register memcache-trace %s", (module, object_path, command))

            hook = _memcache_trace_import_hook(object_path, command)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup name transaction wrapper defined in configuration file.


def _transaction_name_import_hook(object_path, name, group, priority):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap transaction-name %s", ((target, func, name, group, priority),))
                newrelic.api.transaction_name.wrap_transaction_name(target, func, name, group, priority)
        except Exception:
            _raise_instrumentation_error("transaction-name", locals())

    return _instrument


def _process_transaction_name_configuration():
    for section in _config_object.sections():
        # Support 'name-transaction' for backward compatibility.
        if not section.startswith("transaction-name:") and not section.startswith("name-transaction:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            name = None
            group = "Function"
            priority = None

            if _config_object.has_option(section, "name"):
                name = _config_object.get(section, "name")
            if _config_object.has_option(section, "group"):
                group = _config_object.get(section, "group")
            if _config_object.has_option(section, "priority"):
                priority = _config_object.getint(section, "priority")

            if name and name.startswith("lambda "):
                callable_vars = {"callable_name": callable_name}
                name = eval(name, callable_vars)  # noqa: S307

            _logger.debug("register transaction-name %s", ((module, object_path, name, group, priority),))

            hook = _transaction_name_import_hook(object_path, name, group, priority)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Setup error trace wrapper defined in configuration file.


def _error_trace_import_hook(object_path, ignore, expected):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap error-trace %s", (target, func, ignore, expected))
                newrelic.api.error_trace.wrap_error_trace(target, func, ignore, expected, None)
        except Exception:
            _raise_instrumentation_error("error-trace", locals())

    return _instrument


def _process_error_trace_configuration():
    for section in _config_object.sections():
        if not section.startswith("error-trace:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            ignore_classes = []
            expected_classes = []

            if _config_object.has_option(section, "ignore_classes"):
                ignore_classes = _config_object.get(section, "ignore_classes").split()

            if _config_object.has_option(section, "ignore_errors"):
                if _config_object.has_option(section, "ignore_classes"):
                    _logger.info("Ignoring deprecated setting: ignore_errors. Please use new setting: ignore_classes.")
                else:
                    _logger.info("Deprecated setting found: ignore_errors. Please use new setting: ignore_classes.")
                    ignore_classes = _config_object.get(section, "ignore_errors").split()

            if _config_object.has_option(section, "expected_classes"):
                expected_classes = _config_object.get(section, "expected_classes").split()

            _logger.debug("register error-trace %s", (module, object_path, ignore_classes, expected_classes))

            hook = _error_trace_import_hook(object_path, ignore_classes, expected_classes)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


# Automatic data source loading defined in configuration file.

_data_sources = []


def _process_data_source_configuration():
    for section in _config_object.sections():
        if not section.startswith("data-source:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            application = None
            name = None
            settings = {}
            properties = {}

            if _config_object.has_option(section, "application"):
                application = _config_object.get(section, "application")
            if _config_object.has_option(section, "name"):
                name = _config_object.get(section, "name")

            if _config_object.has_option(section, "settings"):
                config_section = _config_object.get(section, "settings")
                settings.update(_config_object.items(config_section))

            properties.update(_config_object.items(section))

            properties.pop("enabled", None)
            properties.pop("function", None)
            properties.pop("application", None)
            properties.pop("name", None)
            properties.pop("settings", None)

            _logger.debug("register data-source %s", (module, object_path, name))

            _data_sources.append((section, module, object_path, application, name, settings, properties))
        except Exception:
            _raise_configuration_error(section)


def _startup_data_source():
    _logger.debug("Registering data sources defined in configuration.")

    agent_instance = newrelic.core.agent.agent_instance()

    for section, module, object_path, application, name, settings, properties in _data_sources:
        try:
            source = getattr(newrelic.api.import_hook.import_module(module), object_path)

            agent_instance.register_data_source(source, application, name, settings, **properties)

        except Exception:
            _logger.exception(
                "Attempt to register data source %s:%s with "
                "name %r from section %r of agent configuration file "
                "has failed. Data source will be skipped.",
                module,
                object_path,
                name,
                section,
            )


_data_sources_done = False


def _setup_data_source():
    global _data_sources_done

    if _data_sources_done:
        return

    _data_sources_done = True

    if _data_sources:
        newrelic.core.agent.Agent.run_on_startup(_startup_data_source)


# Setup function profiler defined in configuration file.


def _function_profile_import_hook(object_path, filename, delay, checkpoint):
    def _instrument(target):
        try:
            for func in _module_function_glob(target, object_path):
                _logger.debug("wrap function-profile %s", (target, func, filename, delay, checkpoint))
                newrelic.api.function_profile.wrap_function_profile(target, func, filename, delay, checkpoint)
        except Exception:
            _raise_instrumentation_error("function-profile", locals())

    return _instrument


def _process_function_profile_configuration():
    for section in _config_object.sections():
        if not section.startswith("function-profile:"):
            continue

        enabled = False

        try:
            enabled = _config_object.getboolean(section, "enabled")
        except configparser.NoOptionError:
            pass
        except Exception:
            _raise_configuration_error(section)

        if not enabled:
            continue

        try:
            function = _config_object.get(section, "function")
            (module, object_path) = function.split(":", 1)

            filename = None
            delay = 1.0
            checkpoint = 30

            filename = _config_object.get(section, "filename")

            if _config_object.has_option(section, "delay"):
                delay = _config_object.getfloat(section, "delay")
            if _config_object.has_option(section, "checkpoint"):
                checkpoint = _config_object.getfloat(section, "checkpoint")

            _logger.debug("register function-profile %s", ((module, object_path, filename, delay, checkpoint),))

            hook = _function_profile_import_hook(object_path, filename, delay, checkpoint)
            newrelic.api.import_hook.register_import_hook(module, hook)
        except Exception:
            _raise_configuration_error(section)


def _process_module_definition(target, module, function="instrument"):
    enabled = True
    execute = None

    # XXX This check makes the following checks to see if import hook
    # was defined in agent configuration file redundant. Leave it as is
    # for now until can clean up whole configuration system.

    if target in _module_import_hook_registry:
        return

    try:
        section = f"import-hook:{target}"
        if _config_object.has_section(section):
            enabled = _config_object.getboolean(section, "enabled")
    except configparser.NoOptionError:
        pass
    except Exception:
        _raise_configuration_error(section)

    try:
        if _config_object.has_option(section, "execute"):
            execute = _config_object.get(section, "execute")

    except Exception:
        _raise_configuration_error(section)

    try:
        if enabled and not execute:
            _module_import_hook_registry[target] = (module, function)

            _logger.debug("register module %s", (target, module, function))

            newrelic.api.import_hook.register_import_hook(target, _module_import_hook(target, module, function))

            _module_import_hook_results.setdefault((target, module, function), None)

    except Exception:
        _raise_instrumentation_error("import-hook", locals())


ASYNCIO_HOOK = ("asyncio", "newrelic.core.trace_cache", "asyncio_loaded")
GREENLET_HOOK = ("greenlet", "newrelic.core.trace_cache", "greenlet_loaded")


def _process_trace_cache_import_hooks():
    _process_module_definition(*GREENLET_HOOK)

    if GREENLET_HOOK not in _module_import_hook_results:
        pass
    elif _module_import_hook_results[GREENLET_HOOK] is None:
        trace_cache.trace_cache().greenlet = False

    _process_module_definition(*ASYNCIO_HOOK)

    if ASYNCIO_HOOK not in _module_import_hook_results:
        pass
    elif _module_import_hook_results[ASYNCIO_HOOK] is None:
        trace_cache.trace_cache().asyncio = False


def _process_module_builtin_defaults():
    _process_module_definition(
        "openai.api_resources.embedding", "newrelic.hooks.mlmodel_openai", "instrument_openai_api_resources_embedding"
    )
    _process_module_definition(
        "openai.api_resources.chat_completion",
        "newrelic.hooks.mlmodel_openai",
        "instrument_openai_api_resources_chat_completion",
    )
    _process_module_definition(
        "openai.resources.embeddings", "newrelic.hooks.mlmodel_openai", "instrument_openai_resources_embeddings"
    )
    _process_module_definition("openai.util", "newrelic.hooks.mlmodel_openai", "instrument_openai_util")
    _process_module_definition(
        "openai.api_resources.abstract.engine_api_resource",
        "newrelic.hooks.mlmodel_openai",
        "instrument_openai_api_resources_abstract_engine_api_resource",
    )
    _process_module_definition("openai._streaming", "newrelic.hooks.mlmodel_openai", "instrument_openai__streaming")

    _process_module_definition(
        "openai.resources.chat.completions",
        "newrelic.hooks.mlmodel_openai",
        "instrument_openai_resources_chat_completions",
    )

    _process_module_definition(
        "openai.resources.completions", "newrelic.hooks.mlmodel_openai", "instrument_openai_resources_chat_completions"
    )
    _process_module_definition("openai._base_client", "newrelic.hooks.mlmodel_openai", "instrument_openai_base_client")

    _process_module_definition("google.genai.models", "newrelic.hooks.mlmodel_gemini", "instrument_genai_models")

    _process_module_definition(
        "asyncio.base_events", "newrelic.hooks.coroutines_asyncio", "instrument_asyncio_base_events"
    )

    _process_module_definition(
        "langchain_core.runnables.base",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_runnables_chains_base",
    )
    _process_module_definition(
        "langchain_core.runnables.config",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_core_runnables_config",
    )
    _process_module_definition(
        "langchain.chains.base", "newrelic.hooks.mlmodel_langchain", "instrument_langchain_chains_base"
    )
    _process_module_definition(
        "langchain_core.callbacks.manager", "newrelic.hooks.mlmodel_langchain", "instrument_langchain_callbacks_manager"
    )

    # VectorStores with similarity_search method
    _process_module_definition(
        "langchain_community.vectorstores.docarray",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.alibabacloud_opensearch",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.redis",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.aerospike",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.analyticdb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.annoy",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.apache_doris",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.aperturedb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.astradb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.atlas",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.awadb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.azure_cosmos_db_no_sql",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.azure_cosmos_db",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.azuresearch",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.bageldb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.baiduvectordb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.baiducloud_vector_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.bigquery_vector_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )
    _process_module_definition(
        "langchain_community.vectorstores.cassandra",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.chroma",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.clarifai",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.clickhouse",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.couchbase",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.dashvector",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.databricks_vector_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.deeplake",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.dingo",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.documentdb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.duckdb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.ecloud_vector_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.elastic_vector_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.elasticsearch",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.epsilla",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.faiss",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.hanavector",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.hippo",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.hologres",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.infinispanvs",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.inmemory",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.kdbai",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.kinetica",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.lancedb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.lantern",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.llm_rails",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.manticore_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.marqo",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.matching_engine",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.meilisearch",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.milvus",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.momento_vector_index",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.mongodb_atlas",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.myscale",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.neo4j_vector",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.thirdai_neuraldb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.nucliadb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.opensearch_vector_search",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.oraclevs",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.pathway",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.pgembedding",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.pgvecto_rs",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.pgvector",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.pinecone",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.qdrant",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.relyt",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.rocksetdb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.scann",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.semadb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.singlestoredb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.sklearn",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.sqlitevec",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.sqlitevss",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.starrocks",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.supabase",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.surrealdb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.tair",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.tencentvectordb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.thirdai_neuraldb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.tidb_vector",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.tigris",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.tiledb",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.timescalevector",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.typesense",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.upstash",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.usearch",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.vald",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.vdms",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.vearch",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.vectara",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.vespa",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.vlite",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.weaviate",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.xata",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.yellowbrick",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.zep_cloud",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.zep",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_community.vectorstores.tablestore",
        "newrelic.hooks.mlmodel_langchain",
        "instrument_langchain_vectorstore_similarity_search",
    )

    _process_module_definition(
        "langchain_core.tools", "newrelic.hooks.mlmodel_langchain", "instrument_langchain_core_tools"
    )

    _process_module_definition(
        "langchain_core.callbacks.manager", "newrelic.hooks.mlmodel_langchain", "instrument_langchain_callbacks_manager"
    )

    _process_module_definition("asyncio.events", "newrelic.hooks.coroutines_asyncio", "instrument_asyncio_events")

    _process_module_definition("asgiref.sync", "newrelic.hooks.adapter_asgiref", "instrument_asgiref_sync")

    _process_module_definition(
        "django.core.handlers.base", "newrelic.hooks.framework_django", "instrument_django_core_handlers_base"
    )
    _process_module_definition(
        "django.core.handlers.asgi", "newrelic.hooks.framework_django", "instrument_django_core_handlers_asgi"
    )
    _process_module_definition(
        "django.core.handlers.wsgi", "newrelic.hooks.framework_django", "instrument_django_core_handlers_wsgi"
    )
    _process_module_definition(
        "django.core.urlresolvers", "newrelic.hooks.framework_django", "instrument_django_core_urlresolvers"
    )
    _process_module_definition("django.template", "newrelic.hooks.framework_django", "instrument_django_template")
    _process_module_definition(
        "django.template.loader_tags", "newrelic.hooks.framework_django", "instrument_django_template_loader_tags"
    )
    _process_module_definition(
        "django.core.servers.basehttp", "newrelic.hooks.framework_django", "instrument_django_core_servers_basehttp"
    )
    _process_module_definition(
        "django.contrib.staticfiles.views",
        "newrelic.hooks.framework_django",
        "instrument_django_contrib_staticfiles_views",
    )
    _process_module_definition(
        "django.contrib.staticfiles.handlers",
        "newrelic.hooks.framework_django",
        "instrument_django_contrib_staticfiles_handlers",
    )
    _process_module_definition("django.views.debug", "newrelic.hooks.framework_django", "instrument_django_views_debug")
    _process_module_definition(
        "django.http.multipartparser", "newrelic.hooks.framework_django", "instrument_django_http_multipartparser"
    )
    _process_module_definition("django.core.mail", "newrelic.hooks.framework_django", "instrument_django_core_mail")
    _process_module_definition(
        "django.core.mail.message", "newrelic.hooks.framework_django", "instrument_django_core_mail_message"
    )
    _process_module_definition(
        "django.views.generic.base", "newrelic.hooks.framework_django", "instrument_django_views_generic_base"
    )
    _process_module_definition(
        "django.core.management.base", "newrelic.hooks.framework_django", "instrument_django_core_management_base"
    )
    _process_module_definition(
        "django.template.base", "newrelic.hooks.framework_django", "instrument_django_template_base"
    )
    _process_module_definition(
        "django.middleware.gzip", "newrelic.hooks.framework_django", "instrument_django_gzip_middleware"
    )

    # New modules in Django 1.10
    _process_module_definition(
        "django.urls.resolvers", "newrelic.hooks.framework_django", "instrument_django_core_urlresolvers"
    )
    _process_module_definition("django.urls.base", "newrelic.hooks.framework_django", "instrument_django_urls_base")
    _process_module_definition(
        "django.core.handlers.exception", "newrelic.hooks.framework_django", "instrument_django_core_handlers_exception"
    )

    _process_module_definition("falcon.api", "newrelic.hooks.framework_falcon", "instrument_falcon_api")
    _process_module_definition("falcon.app", "newrelic.hooks.framework_falcon", "instrument_falcon_app")
    _process_module_definition(
        "falcon.routing.util", "newrelic.hooks.framework_falcon", "instrument_falcon_routing_util"
    )

    _process_module_definition("fastapi.routing", "newrelic.hooks.framework_fastapi", "instrument_fastapi_routing")

    _process_module_definition("flask.app", "newrelic.hooks.framework_flask", "instrument_flask_app")
    _process_module_definition("flask.templating", "newrelic.hooks.framework_flask", "instrument_flask_templating")
    _process_module_definition("flask.blueprints", "newrelic.hooks.framework_flask", "instrument_flask_blueprints")
    _process_module_definition("flask.views", "newrelic.hooks.framework_flask", "instrument_flask_views")

    _process_module_definition(
        "flask_compress", "newrelic.hooks.middleware_flask_compress", "instrument_flask_compress"
    )

    _process_module_definition("flask_restful", "newrelic.hooks.component_flask_rest", "instrument_flask_rest")
    _process_module_definition("flask_restplus.api", "newrelic.hooks.component_flask_rest", "instrument_flask_rest")
    _process_module_definition("flask_restx.api", "newrelic.hooks.component_flask_rest", "instrument_flask_rest")

    _process_module_definition("graphql_server", "newrelic.hooks.component_graphqlserver", "instrument_graphqlserver")

    _process_module_definition(
        "sentry_sdk.integrations.asgi", "newrelic.hooks.component_sentry", "instrument_sentry_sdk_integrations_asgi"
    )

    _process_module_definition("httpx._client", "newrelic.hooks.external_httpx", "instrument_httpx_client")

    _process_module_definition("gluon.contrib.feedparser", "newrelic.hooks.external_feedparser")
    _process_module_definition("gluon.contrib.memcache.memcache", "newrelic.hooks.memcache_memcache")

    _process_module_definition(
        "graphene.types.schema", "newrelic.hooks.framework_graphene", "instrument_graphene_types_schema"
    )

    _process_module_definition("graphql.graphql", "newrelic.hooks.framework_graphql", "instrument_graphql")
    _process_module_definition(
        "graphql.execution.execute", "newrelic.hooks.framework_graphql", "instrument_graphql_execute"
    )
    _process_module_definition(
        "graphql.execution.executor", "newrelic.hooks.framework_graphql", "instrument_graphql_execute"
    )
    _process_module_definition(
        "graphql.execution.middleware", "newrelic.hooks.framework_graphql", "instrument_graphql_execution_middleware"
    )
    _process_module_definition(
        "graphql.execution.utils", "newrelic.hooks.framework_graphql", "instrument_graphql_execution_utils"
    )
    _process_module_definition(
        "graphql.error.located_error", "newrelic.hooks.framework_graphql", "instrument_graphql_error_located_error"
    )
    _process_module_definition(
        "graphql.language.parser", "newrelic.hooks.framework_graphql", "instrument_graphql_parser"
    )
    _process_module_definition(
        "graphql.validation.validate", "newrelic.hooks.framework_graphql", "instrument_graphql_validate"
    )
    _process_module_definition(
        "graphql.validation.validation", "newrelic.hooks.framework_graphql", "instrument_graphql_validate"
    )

    _process_module_definition(
        "graphql.type.schema", "newrelic.hooks.framework_graphql", "instrument_graphql_schema_get_field"
    )

    _process_module_definition(
        "google.cloud.firestore_v1.base_client",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_base_client",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.client",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_client",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_client",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_client",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.document",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_document",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_document",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_document",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.collection",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_collection",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_collection",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_collection",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.query",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_query",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_query",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_query",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.aggregation",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_aggregation",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_aggregation",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_aggregation",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.batch",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_batch",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_batch",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_batch",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.bulk_batch",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_bulk_batch",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.transaction",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_transaction",
    )
    _process_module_definition(
        "google.cloud.firestore_v1.async_transaction",
        "newrelic.hooks.datastore_firestore",
        "instrument_google_cloud_firestore_v1_async_transaction",
    )

    _process_module_definition("ariadne.asgi", "newrelic.hooks.framework_ariadne", "instrument_ariadne_asgi")
    _process_module_definition("ariadne.graphql", "newrelic.hooks.framework_ariadne", "instrument_ariadne_execute")
    _process_module_definition("ariadne.wsgi", "newrelic.hooks.framework_ariadne", "instrument_ariadne_wsgi")

    _process_module_definition("grpc._channel", "newrelic.hooks.framework_grpc", "instrument_grpc__channel")
    _process_module_definition("grpc._server", "newrelic.hooks.framework_grpc", "instrument_grpc_server")

    _process_module_definition("bottle", "newrelic.hooks.framework_bottle", "instrument_bottle")

    _process_module_definition(
        "cherrypy._cpreqbody", "newrelic.hooks.framework_cherrypy", "instrument_cherrypy__cpreqbody"
    )
    _process_module_definition(
        "cherrypy._cprequest", "newrelic.hooks.framework_cherrypy", "instrument_cherrypy__cprequest"
    )
    _process_module_definition(
        "cherrypy._cpdispatch", "newrelic.hooks.framework_cherrypy", "instrument_cherrypy__cpdispatch"
    )
    _process_module_definition("cherrypy._cpwsgi", "newrelic.hooks.framework_cherrypy", "instrument_cherrypy__cpwsgi")
    _process_module_definition("cherrypy._cptree", "newrelic.hooks.framework_cherrypy", "instrument_cherrypy__cptree")

    _process_module_definition(
        "confluent_kafka.cimpl", "newrelic.hooks.messagebroker_confluentkafka", "instrument_confluentkafka_cimpl"
    )
    _process_module_definition(
        "confluent_kafka.serializing_producer",
        "newrelic.hooks.messagebroker_confluentkafka",
        "instrument_confluentkafka_serializing_producer",
    )
    _process_module_definition(
        "confluent_kafka.deserializing_consumer",
        "newrelic.hooks.messagebroker_confluentkafka",
        "instrument_confluentkafka_deserializing_consumer",
    )

    _process_module_definition(
        "kafka.consumer.group", "newrelic.hooks.messagebroker_kafkapython", "instrument_kafka_consumer_group"
    )
    _process_module_definition(
        "kafka.producer.kafka", "newrelic.hooks.messagebroker_kafkapython", "instrument_kafka_producer"
    )
    _process_module_definition(
        "kafka.coordinator.heartbeat", "newrelic.hooks.messagebroker_kafkapython", "instrument_kafka_heartbeat"
    )
    _process_module_definition("kombu.messaging", "newrelic.hooks.messagebroker_kombu", "instrument_kombu_messaging")
    _process_module_definition(
        "kombu.serialization", "newrelic.hooks.messagebroker_kombu", "instrument_kombu_serializaion"
    )
    _process_module_definition("logging", "newrelic.hooks.logger_logging", "instrument_logging")

    _process_module_definition("loguru", "newrelic.hooks.logger_loguru", "instrument_loguru")
    _process_module_definition("loguru._logger", "newrelic.hooks.logger_loguru", "instrument_loguru_logger")

    _process_module_definition("mcp.client.session", "newrelic.hooks.adapter_mcp", "instrument_mcp_client_session")

    _process_module_definition("structlog._base", "newrelic.hooks.logger_structlog", "instrument_structlog__base")
    _process_module_definition("structlog._frames", "newrelic.hooks.logger_structlog", "instrument_structlog__frames")
    _process_module_definition("paste.httpserver", "newrelic.hooks.adapter_paste", "instrument_paste_httpserver")

    _process_module_definition("gunicorn.app.base", "newrelic.hooks.adapter_gunicorn", "instrument_gunicorn_app_base")

    _process_module_definition("cassandra", "newrelic.hooks.datastore_cassandradriver", "instrument_cassandra")
    _process_module_definition(
        "cassandra.cluster", "newrelic.hooks.datastore_cassandradriver", "instrument_cassandra_cluster"
    )

    _process_module_definition("cx_Oracle", "newrelic.hooks.database_cx_oracle", "instrument_cx_oracle")

    _process_module_definition("oracledb", "newrelic.hooks.database_oracledb", "instrument_oracledb")

    _process_module_definition("ibm_db_dbi", "newrelic.hooks.database_ibm_db_dbi", "instrument_ibm_db_dbi")

    _process_module_definition("mysql.connector", "newrelic.hooks.database_mysql", "instrument_mysql_connector")
    _process_module_definition("MySQLdb", "newrelic.hooks.database_mysqldb", "instrument_mysqldb")
    _process_module_definition("pymysql", "newrelic.hooks.database_pymysql", "instrument_pymysql")

    _process_module_definition("aiomysql", "newrelic.hooks.database_aiomysql", "instrument_aiomysql")
    _process_module_definition("aiomysql.pool", "newrelic.hooks.database_aiomysql", "instrument_aiomysql_pool")

    _process_module_definition("pyodbc", "newrelic.hooks.database_pyodbc", "instrument_pyodbc")

    _process_module_definition("pymssql", "newrelic.hooks.database_pymssql", "instrument_pymssql")

    _process_module_definition("psycopg", "newrelic.hooks.database_psycopg", "instrument_psycopg")
    _process_module_definition("psycopg.sql", "newrelic.hooks.database_psycopg", "instrument_psycopg_sql")

    _process_module_definition("psycopg2", "newrelic.hooks.database_psycopg2", "instrument_psycopg2")
    _process_module_definition(
        "psycopg2._psycopg2", "newrelic.hooks.database_psycopg2", "instrument_psycopg2__psycopg2"
    )
    _process_module_definition(
        "psycopg2.extensions", "newrelic.hooks.database_psycopg2", "instrument_psycopg2_extensions"
    )
    _process_module_definition("psycopg2._json", "newrelic.hooks.database_psycopg2", "instrument_psycopg2__json")
    _process_module_definition("psycopg2._range", "newrelic.hooks.database_psycopg2", "instrument_psycopg2__range")
    _process_module_definition("psycopg2.sql", "newrelic.hooks.database_psycopg2", "instrument_psycopg2_sql")

    _process_module_definition("psycopg2ct", "newrelic.hooks.database_psycopg2ct", "instrument_psycopg2ct")
    _process_module_definition(
        "psycopg2ct.extensions", "newrelic.hooks.database_psycopg2ct", "instrument_psycopg2ct_extensions"
    )

    _process_module_definition("psycopg2cffi", "newrelic.hooks.database_psycopg2cffi", "instrument_psycopg2cffi")
    _process_module_definition(
        "psycopg2cffi.extensions", "newrelic.hooks.database_psycopg2cffi", "instrument_psycopg2cffi_extensions"
    )

    _process_module_definition(
        "asyncpg.connect_utils", "newrelic.hooks.database_asyncpg", "instrument_asyncpg_connect_utils"
    )
    _process_module_definition("asyncpg.protocol", "newrelic.hooks.database_asyncpg", "instrument_asyncpg_protocol")

    _process_module_definition(
        "postgresql.driver.dbapi20", "newrelic.hooks.database_postgresql", "instrument_postgresql_driver_dbapi20"
    )

    _process_module_definition(
        "postgresql.interface.proboscis.dbapi2",
        "newrelic.hooks.database_postgresql",
        "instrument_postgresql_interface_proboscis_dbapi2",
    )

    _process_module_definition("sqlite3", "newrelic.hooks.database_sqlite", "instrument_sqlite3")
    _process_module_definition("sqlite3.dbapi2", "newrelic.hooks.database_sqlite", "instrument_sqlite3_dbapi2")

    _process_module_definition("pysqlite2", "newrelic.hooks.database_sqlite", "instrument_sqlite3")
    _process_module_definition("pysqlite2.dbapi2", "newrelic.hooks.database_sqlite", "instrument_sqlite3_dbapi2")

    _process_module_definition("memcache", "newrelic.hooks.datastore_memcache", "instrument_memcache")
    _process_module_definition("pylibmc.client", "newrelic.hooks.datastore_pylibmc", "instrument_pylibmc_client")
    _process_module_definition(
        "bmemcached.client", "newrelic.hooks.datastore_bmemcached", "instrument_bmemcached_client"
    )
    _process_module_definition(
        "pymemcache.client", "newrelic.hooks.datastore_pymemcache", "instrument_pymemcache_client"
    )
    _process_module_definition("aiomcache.client", "newrelic.hooks.datastore_aiomcache", "instrument_aiomcache_client")

    _process_module_definition("jinja2.environment", "newrelic.hooks.template_jinja2")

    _process_module_definition("mako.runtime", "newrelic.hooks.template_mako", "instrument_mako_runtime")
    _process_module_definition("mako.template", "newrelic.hooks.template_mako", "instrument_mako_template")

    _process_module_definition("genshi.template.base", "newrelic.hooks.template_genshi")

    _process_module_definition("http.client", "newrelic.hooks.external_httplib")

    _process_module_definition("httplib2", "newrelic.hooks.external_httplib2")

    _process_module_definition("urllib.request", "newrelic.hooks.external_urllib")

    _process_module_definition(
        "urllib3.connectionpool", "newrelic.hooks.external_urllib3", "instrument_urllib3_connectionpool"
    )
    _process_module_definition("urllib3.connection", "newrelic.hooks.external_urllib3", "instrument_urllib3_connection")
    _process_module_definition(
        "requests.packages.urllib3.connection", "newrelic.hooks.external_urllib3", "instrument_urllib3_connection"
    )

    _process_module_definition(
        "starlette.requests", "newrelic.hooks.framework_starlette", "instrument_starlette_requests"
    )
    _process_module_definition(
        "starlette.routing", "newrelic.hooks.framework_starlette", "instrument_starlette_routing"
    )
    _process_module_definition(
        "starlette.applications", "newrelic.hooks.framework_starlette", "instrument_starlette_applications"
    )
    _process_module_definition(
        "starlette.middleware.errors", "newrelic.hooks.framework_starlette", "instrument_starlette_middleware_errors"
    )
    _process_module_definition(
        "starlette.middleware.exceptions",
        "newrelic.hooks.framework_starlette",
        "instrument_starlette_middleware_exceptions",
    )
    _process_module_definition(
        "starlette.exceptions", "newrelic.hooks.framework_starlette", "instrument_starlette_exceptions"
    )
    _process_module_definition(
        "starlette.background", "newrelic.hooks.framework_starlette", "instrument_starlette_background_task"
    )
    _process_module_definition(
        "starlette.concurrency", "newrelic.hooks.framework_starlette", "instrument_starlette_concurrency"
    )

    _process_module_definition("strawberry.asgi", "newrelic.hooks.framework_strawberry", "instrument_strawberry_asgi")

    _process_module_definition(
        "strawberry.schema.schema", "newrelic.hooks.framework_strawberry", "instrument_strawberry_schema"
    )

    _process_module_definition(
        "strawberry.schema.schema_converter",
        "newrelic.hooks.framework_strawberry",
        "instrument_strawberry_schema_converter",
    )

    _process_module_definition("uvicorn.config", "newrelic.hooks.adapter_uvicorn", "instrument_uvicorn_config")

    _process_module_definition(
        "hypercorn.asyncio.run", "newrelic.hooks.adapter_hypercorn", "instrument_hypercorn_asyncio_run"
    )
    _process_module_definition(
        "hypercorn.trio.run", "newrelic.hooks.adapter_hypercorn", "instrument_hypercorn_trio_run"
    )
    _process_module_definition("hypercorn.utils", "newrelic.hooks.adapter_hypercorn", "instrument_hypercorn_utils")

    _process_module_definition("daphne.server", "newrelic.hooks.adapter_daphne", "instrument_daphne_server")

    _process_module_definition("sanic.app", "newrelic.hooks.framework_sanic", "instrument_sanic_app")
    _process_module_definition("sanic.response", "newrelic.hooks.framework_sanic", "instrument_sanic_response")
    _process_module_definition(
        "sanic.touchup.service", "newrelic.hooks.framework_sanic", "instrument_sanic_touchup_service"
    )

    _process_module_definition("aiohttp.wsgi", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_wsgi")
    _process_module_definition("aiohttp.web", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_web")
    _process_module_definition(
        "aiohttp.web_reqrep", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_web_response"
    )
    _process_module_definition(
        "aiohttp.web_response", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_web_response"
    )
    _process_module_definition(
        "aiohttp.web_urldispatcher", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_web_urldispatcher"
    )
    _process_module_definition("aiohttp.client", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_client")
    _process_module_definition(
        "aiohttp.client_reqrep", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_client_reqrep"
    )
    _process_module_definition("aiohttp.protocol", "newrelic.hooks.framework_aiohttp", "instrument_aiohttp_protocol")

    _process_module_definition("requests.api", "newrelic.hooks.external_requests", "instrument_requests_api")
    _process_module_definition("requests.sessions", "newrelic.hooks.external_requests", "instrument_requests_sessions")

    _process_module_definition("feedparser", "newrelic.hooks.external_feedparser")

    _process_module_definition("xmlrpclib", "newrelic.hooks.external_xmlrpclib")

    _process_module_definition("dropbox", "newrelic.hooks.external_dropbox")

    _process_module_definition("facepy.graph_api", "newrelic.hooks.external_facepy")

    _process_module_definition("pysolr", "newrelic.hooks.datastore_pysolr", "instrument_pysolr")

    _process_module_definition("solr", "newrelic.hooks.datastore_solrpy", "instrument_solrpy")

    _process_module_definition("aredis.client", "newrelic.hooks.datastore_aredis", "instrument_aredis_client")

    _process_module_definition("aredis.connection", "newrelic.hooks.datastore_aredis", "instrument_aredis_connection")

    _process_module_definition("aioredis.client", "newrelic.hooks.datastore_aioredis", "instrument_aioredis_client")

    _process_module_definition("aioredis.commands", "newrelic.hooks.datastore_aioredis", "instrument_aioredis_client")

    _process_module_definition(
        "aioredis.connection", "newrelic.hooks.datastore_aioredis", "instrument_aioredis_connection"
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.client", "newrelic.hooks.datastore_elasticsearch", "instrument_elasticsearch_client"
    )
    _process_module_definition(
        "elasticsearch._async.client",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client", "newrelic.hooks.datastore_elasticsearch", "instrument_elasticsearch_client_v8"
    )
    _process_module_definition(
        "elasticsearch._async.client",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_v8",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.client.cat", "newrelic.hooks.datastore_elasticsearch", "instrument_elasticsearch_client_cat"
    )
    _process_module_definition(
        "elasticsearch._async.client.cat",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_cat",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.cat",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_cat_v8",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.client.cluster",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_cluster",
    )
    _process_module_definition(
        "elasticsearch._async.client.cluster",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_cluster",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.cluster",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_cluster_v8",
    )
    # v7 and below
    _process_module_definition(
        "elasticsearch.client.indices",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_indices",
    )
    _process_module_definition(
        "elasticsearch._async.client.indices",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_indices",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.indices",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_indices_v8",
    )
    # v7 and below
    _process_module_definition(
        "elasticsearch.client.nodes", "newrelic.hooks.datastore_elasticsearch", "instrument_elasticsearch_client_nodes"
    )
    _process_module_definition(
        "elasticsearch._async.client.nodes",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_nodes",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.nodes",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_nodes_v8",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.client.snapshot",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_snapshot",
    )
    _process_module_definition(
        "elasticsearch._async.client.snapshot",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_snapshot",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.snapshot",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_snapshot_v8",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.client.tasks", "newrelic.hooks.datastore_elasticsearch", "instrument_elasticsearch_client_tasks"
    )
    _process_module_definition(
        "elasticsearch._async.client.tasks",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_tasks",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.tasks",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_tasks_v8",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.client.ingest",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_ingest",
    )
    _process_module_definition(
        "elasticsearch._async.client.ingest",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch__async_client_ingest",
    )
    # v8 and above
    _process_module_definition(
        "elasticsearch._sync.client.ingest",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_client_ingest_v8",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.connection.base",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elasticsearch_connection_base",
    )
    _process_module_definition(
        "elasticsearch._async.http_aiohttp",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_async_elasticsearch_connection_base",
    )
    # v8 and above
    _process_module_definition(
        "elastic_transport._node._base",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elastic_transport__node__base",
    )
    _process_module_definition(
        "elastic_transport._node._base_async",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_async_elastic_transport__node__base",
    )

    # v7 and below
    _process_module_definition(
        "elasticsearch.transport", "newrelic.hooks.datastore_elasticsearch", "instrument_elasticsearch_transport"
    )
    _process_module_definition(
        "elasticsearch._async.transport",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_async_elasticsearch_transport",
    )
    # v8 and above
    _process_module_definition(
        "elastic_transport._transport",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_elastic_transport__transport",
    )
    _process_module_definition(
        "elastic_transport._async_transport",
        "newrelic.hooks.datastore_elasticsearch",
        "instrument_async_elastic_transport__transport",
    )

    _process_module_definition("pika.adapters", "newrelic.hooks.messagebroker_pika", "instrument_pika_adapters")
    _process_module_definition("pika.channel", "newrelic.hooks.messagebroker_pika", "instrument_pika_channel")
    _process_module_definition("pika.spec", "newrelic.hooks.messagebroker_pika", "instrument_pika_spec")

    _process_module_definition(
        "pyelasticsearch.client", "newrelic.hooks.datastore_pyelasticsearch", "instrument_pyelasticsearch_client"
    )

    # Newer pymongo module locations
    _process_module_definition(
        "pymongo.synchronous.pool", "newrelic.hooks.datastore_pymongo", "instrument_pymongo_synchronous_pool"
    )
    _process_module_definition(
        "pymongo.asynchronous.pool", "newrelic.hooks.datastore_pymongo", "instrument_pymongo_asynchronous_pool"
    )

    _process_module_definition(
        "pymongo.synchronous.collection",
        "newrelic.hooks.datastore_pymongo",
        "instrument_pymongo_synchronous_collection",
    )
    _process_module_definition(
        "pymongo.asynchronous.collection",
        "newrelic.hooks.datastore_pymongo",
        "instrument_pymongo_asynchronous_collection",
    )

    _process_module_definition(
        "pymongo.synchronous.mongo_client",
        "newrelic.hooks.datastore_pymongo",
        "instrument_pymongo_synchronous_mongo_client",
    )
    _process_module_definition(
        "pymongo.asynchronous.mongo_client",
        "newrelic.hooks.datastore_pymongo",
        "instrument_pymongo_asynchronous_mongo_client",
    )

    # Older pymongo module locations
    _process_module_definition(
        "pymongo.connection", "newrelic.hooks.datastore_pymongo", "instrument_pymongo_synchronous_pool"
    )
    _process_module_definition(
        "pymongo.collection", "newrelic.hooks.datastore_pymongo", "instrument_pymongo_synchronous_collection"
    )
    _process_module_definition(
        "pymongo.mongo_client", "newrelic.hooks.datastore_pymongo", "instrument_pymongo_synchronous_mongo_client"
    )

    # Redis v4.2+
    _process_module_definition(
        "redis.asyncio.client", "newrelic.hooks.datastore_redis", "instrument_asyncio_redis_client"
    )

    # Redis v4.2+
    _process_module_definition(
        "redis.asyncio.commands", "newrelic.hooks.datastore_redis", "instrument_asyncio_redis_client"
    )

    # Redis v4.2+
    _process_module_definition(
        "redis.asyncio.connection", "newrelic.hooks.datastore_redis", "instrument_asyncio_redis_connection"
    )

    _process_module_definition("redis.connection", "newrelic.hooks.datastore_redis", "instrument_redis_connection")
    _process_module_definition("redis.client", "newrelic.hooks.datastore_redis", "instrument_redis_client")

    _process_module_definition(
        "redis.commands.cluster", "newrelic.hooks.datastore_redis", "instrument_redis_commands_cluster"
    )

    _process_module_definition(
        "redis.commands.core", "newrelic.hooks.datastore_redis", "instrument_redis_commands_core"
    )

    _process_module_definition(
        "redis.commands.sentinel", "newrelic.hooks.datastore_redis", "instrument_redis_commands_sentinel"
    )

    _process_module_definition(
        "redis.commands.json.commands", "newrelic.hooks.datastore_redis", "instrument_redis_commands_json_commands"
    )

    _process_module_definition(
        "redis.commands.search.commands", "newrelic.hooks.datastore_redis", "instrument_redis_commands_search_commands"
    )

    _process_module_definition(
        "redis.commands.timeseries.commands",
        "newrelic.hooks.datastore_redis",
        "instrument_redis_commands_timeseries_commands",
    )

    _process_module_definition(
        "redis.commands.bf.commands", "newrelic.hooks.datastore_redis", "instrument_redis_commands_bf_commands"
    )

    # Redis version <6.0
    _process_module_definition(
        "redis.commands.graph.commands", "newrelic.hooks.datastore_redis", "instrument_redis_commands_graph_commands"
    )

    # Added in Redis v6.0+
    _process_module_definition(
        "redis.commands.vectorset.commands",
        "newrelic.hooks.datastore_redis",
        "instrument_redis_commands_vectorset_commands",
    )

    _process_module_definition(
        "valkey.asyncio.client", "newrelic.hooks.datastore_valkey", "instrument_asyncio_valkey_client"
    )

    _process_module_definition(
        "valkey.asyncio.commands", "newrelic.hooks.datastore_valkey", "instrument_asyncio_valkey_client"
    )

    _process_module_definition(
        "valkey.asyncio.connection", "newrelic.hooks.datastore_valkey", "instrument_asyncio_valkey_connection"
    )

    _process_module_definition("valkey.connection", "newrelic.hooks.datastore_valkey", "instrument_valkey_connection")
    _process_module_definition("valkey.client", "newrelic.hooks.datastore_valkey", "instrument_valkey_client")

    _process_module_definition(
        "valkey.commands.cluster", "newrelic.hooks.datastore_valkey", "instrument_valkey_commands_cluster"
    )

    _process_module_definition(
        "valkey.commands.core", "newrelic.hooks.datastore_valkey", "instrument_valkey_commands_core"
    )

    _process_module_definition(
        "valkey.commands.sentinel", "newrelic.hooks.datastore_valkey", "instrument_valkey_commands_sentinel"
    )

    _process_module_definition(
        "valkey.commands.json.commands", "newrelic.hooks.datastore_valkey", "instrument_valkey_commands_json_commands"
    )

    _process_module_definition(
        "valkey.commands.search.commands",
        "newrelic.hooks.datastore_valkey",
        "instrument_valkey_commands_search_commands",
    )

    _process_module_definition(
        "valkey.commands.timeseries.commands",
        "newrelic.hooks.datastore_valkey",
        "instrument_valkey_commands_timeseries_commands",
    )

    _process_module_definition(
        "valkey.commands.bf.commands", "newrelic.hooks.datastore_valkey", "instrument_valkey_commands_bf_commands"
    )

    _process_module_definition(
        "valkey.commands.graph.commands", "newrelic.hooks.datastore_valkey", "instrument_valkey_commands_graph_commands"
    )

    _process_module_definition(
        "motor.motor_asyncio", "newrelic.hooks.datastore_motor", "instrument_motor_motor_asyncio"
    )
    _process_module_definition(
        "motor.motor_tornado", "newrelic.hooks.datastore_motor", "instrument_motor_motor_tornado"
    )

    _process_module_definition("piston.resource", "newrelic.hooks.component_piston", "instrument_piston_resource")
    _process_module_definition("piston.doc", "newrelic.hooks.component_piston", "instrument_piston_doc")

    _process_module_definition(
        "tastypie.resources", "newrelic.hooks.component_tastypie", "instrument_tastypie_resources"
    )
    _process_module_definition("tastypie.api", "newrelic.hooks.component_tastypie", "instrument_tastypie_api")

    _process_module_definition("sklearn.metrics", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_metrics")

    _process_module_definition(
        "sklearn.tree._classes", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_tree_models"
    )
    # In scikit-learn < 0.21 the model classes are in tree.py instead of _classes.py.
    _process_module_definition("sklearn.tree.tree", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_tree_models")

    _process_module_definition(
        "sklearn.compose._column_transformer", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_compose_models"
    )

    _process_module_definition(
        "sklearn.compose._target", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_compose_models"
    )

    _process_module_definition(
        "sklearn.covariance._empirical_covariance",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_models",
    )

    _process_module_definition(
        "sklearn.covariance.empirical_covariance_",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_models",
    )

    _process_module_definition(
        "sklearn.covariance.shrunk_covariance_",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_shrunk_models",
    )

    _process_module_definition(
        "sklearn.covariance._shrunk_covariance",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_shrunk_models",
    )

    _process_module_definition(
        "sklearn.covariance.robust_covariance_",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_models",
    )

    _process_module_definition(
        "sklearn.covariance._robust_covariance",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_models",
    )

    _process_module_definition(
        "sklearn.covariance.graph_lasso_",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_graph_models",
    )

    _process_module_definition(
        "sklearn.covariance._graph_lasso",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_graph_models",
    )

    _process_module_definition(
        "sklearn.covariance.elliptic_envelope", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_covariance_models"
    )

    _process_module_definition(
        "sklearn.covariance._elliptic_envelope",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_covariance_models",
    )

    _process_module_definition(
        "sklearn.ensemble._bagging", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_bagging_models"
    )

    _process_module_definition(
        "sklearn.ensemble.bagging", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_bagging_models"
    )

    _process_module_definition(
        "sklearn.ensemble._forest", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_forest_models"
    )

    _process_module_definition(
        "sklearn.ensemble.forest", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_forest_models"
    )

    _process_module_definition(
        "sklearn.ensemble._iforest", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_iforest_models"
    )

    _process_module_definition(
        "sklearn.ensemble.iforest", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_iforest_models"
    )

    _process_module_definition(
        "sklearn.ensemble._weight_boosting",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_ensemble_weight_boosting_models",
    )

    _process_module_definition(
        "sklearn.ensemble.weight_boosting",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_ensemble_weight_boosting_models",
    )

    _process_module_definition(
        "sklearn.ensemble._gb", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_gradient_boosting_models"
    )

    _process_module_definition(
        "sklearn.ensemble.gradient_boosting",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_ensemble_gradient_boosting_models",
    )

    _process_module_definition(
        "sklearn.ensemble._voting", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_voting_models"
    )

    _process_module_definition(
        "sklearn.ensemble.voting_classifier",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_ensemble_voting_models",
    )

    _process_module_definition(
        "sklearn.ensemble._stacking", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_ensemble_stacking_models"
    )

    _process_module_definition(
        "sklearn.ensemble._hist_gradient_boosting.gradient_boosting",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_ensemble_hist_models",
    )

    _process_module_definition(
        "sklearn.linear_model._base", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model.base", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model._bayes", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_bayes_models"
    )

    _process_module_definition(
        "sklearn.linear_model.bayes", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_bayes_models"
    )

    _process_module_definition(
        "sklearn.linear_model._least_angle",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_least_angle_models",
    )

    _process_module_definition(
        "sklearn.linear_model.least_angle",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_least_angle_models",
    )

    _process_module_definition(
        "sklearn.linear_model.coordinate_descent",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_coordinate_descent_models",
    )

    _process_module_definition(
        "sklearn.linear_model._coordinate_descent",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_coordinate_descent_models",
    )

    _process_module_definition(
        "sklearn.linear_model._glm", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_GLM_models"
    )

    _process_module_definition(
        "sklearn.linear_model._huber", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model.huber", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model._stochastic_gradient",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_stochastic_gradient_models",
    )

    _process_module_definition(
        "sklearn.linear_model.stochastic_gradient",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_stochastic_gradient_models",
    )

    _process_module_definition(
        "sklearn.linear_model._ridge", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_ridge_models"
    )

    _process_module_definition(
        "sklearn.linear_model.ridge", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_ridge_models"
    )

    _process_module_definition(
        "sklearn.linear_model._logistic", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_logistic_models"
    )

    _process_module_definition(
        "sklearn.linear_model.logistic", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_logistic_models"
    )

    _process_module_definition(
        "sklearn.linear_model._omp", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_OMP_models"
    )

    _process_module_definition(
        "sklearn.linear_model.omp", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_OMP_models"
    )

    _process_module_definition(
        "sklearn.linear_model._passive_aggressive",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_passive_aggressive_models",
    )

    _process_module_definition(
        "sklearn.linear_model.passive_aggressive",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_linear_passive_aggressive_models",
    )

    _process_module_definition(
        "sklearn.linear_model._perceptron", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model.perceptron", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model._quantile", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model._ransac", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model.ransac", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model._theil_sen", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.linear_model.theil_sen", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_linear_models"
    )

    _process_module_definition(
        "sklearn.cross_decomposition._pls",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_cross_decomposition_models",
    )

    _process_module_definition(
        "sklearn.cross_decomposition.pls_",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_cross_decomposition_models",
    )

    _process_module_definition(
        "sklearn.discriminant_analysis",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_discriminant_analysis_models",
    )

    _process_module_definition(
        "sklearn.gaussian_process._gpc", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_gaussian_process_models"
    )

    _process_module_definition(
        "sklearn.gaussian_process.gpc", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_gaussian_process_models"
    )

    _process_module_definition(
        "sklearn.gaussian_process._gpr", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_gaussian_process_models"
    )

    _process_module_definition(
        "sklearn.gaussian_process.gpr", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_gaussian_process_models"
    )

    _process_module_definition("sklearn.dummy", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_dummy_models")

    _process_module_definition(
        "sklearn.feature_selection._rfe",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_rfe_models",
    )

    _process_module_definition(
        "sklearn.feature_selection.rfe",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_rfe_models",
    )

    _process_module_definition(
        "sklearn.feature_selection._variance_threshold",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_models",
    )

    _process_module_definition(
        "sklearn.feature_selection.variance_threshold",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_models",
    )

    _process_module_definition(
        "sklearn.feature_selection._from_model",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_models",
    )

    _process_module_definition(
        "sklearn.feature_selection.from_model",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_models",
    )

    _process_module_definition(
        "sklearn.feature_selection._sequential",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_feature_selection_models",
    )

    _process_module_definition(
        "sklearn.kernel_ridge", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_kernel_ridge_models"
    )

    _process_module_definition(
        "sklearn.neural_network._multilayer_perceptron",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_neural_network_models",
    )

    _process_module_definition(
        "sklearn.neural_network.multilayer_perceptron",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_neural_network_models",
    )

    _process_module_definition(
        "sklearn.neural_network._rbm", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neural_network_models"
    )

    _process_module_definition(
        "sklearn.neural_network.rbm", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neural_network_models"
    )

    _process_module_definition(
        "sklearn.calibration", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_calibration_models"
    )

    _process_module_definition(
        "sklearn.cluster._affinity_propagation", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster.affinity_propagation_", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster._agglomerative",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_cluster_agglomerative_models",
    )

    _process_module_definition(
        "sklearn.cluster.hierarchical",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_cluster_agglomerative_models",
    )

    _process_module_definition(
        "sklearn.cluster._birch", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster.birch", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster._bisect_k_means", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_kmeans_models"
    )

    _process_module_definition(
        "sklearn.cluster._dbscan", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster.dbscan_", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster._feature_agglomeration", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster._kmeans", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_kmeans_models"
    )

    _process_module_definition(
        "sklearn.cluster.k_means_", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_kmeans_models"
    )

    _process_module_definition(
        "sklearn.cluster._mean_shift", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster.mean_shift_", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster._optics", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_models"
    )

    _process_module_definition(
        "sklearn.cluster._spectral", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_clustering_models"
    )

    _process_module_definition(
        "sklearn.cluster.spectral", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_clustering_models"
    )

    _process_module_definition(
        "sklearn.cluster._bicluster", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_clustering_models"
    )

    _process_module_definition(
        "sklearn.cluster.bicluster", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_cluster_clustering_models"
    )

    _process_module_definition(
        "sklearn.multiclass", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_multiclass_models"
    )

    _process_module_definition(
        "sklearn.multioutput", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_multioutput_models"
    )

    _process_module_definition(
        "sklearn.naive_bayes", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_naive_bayes_models"
    )

    _process_module_definition(
        "sklearn.model_selection._search", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_model_selection_models"
    )

    _process_module_definition(
        "sklearn.mixture._bayesian_mixture", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_mixture_models"
    )

    _process_module_definition(
        "sklearn.mixture.bayesian_mixture", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_mixture_models"
    )

    _process_module_definition(
        "sklearn.mixture._gaussian_mixture", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_mixture_models"
    )

    _process_module_definition(
        "sklearn.mixture.gaussian_mixture", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_mixture_models"
    )

    _process_module_definition(
        "sklearn.pipeline", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_pipeline_models"
    )

    _process_module_definition(
        "sklearn.semi_supervised._label_propagation",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_semi_supervised_models",
    )

    _process_module_definition(
        "sklearn.semi_supervised._self_training",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_semi_supervised_models",
    )

    _process_module_definition(
        "sklearn.semi_supervised.label_propagation",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_semi_supervised_models",
    )

    _process_module_definition(
        "sklearn.svm._classes", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_svm_models"
    )

    _process_module_definition("sklearn.svm.classes", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_svm_models")

    _process_module_definition(
        "sklearn.neighbors._classification",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_neighbors_KRadius_models",
    )

    _process_module_definition(
        "sklearn.neighbors.classification",
        "newrelic.hooks.mlmodel_sklearn",
        "instrument_sklearn_neighbors_KRadius_models",
    )

    _process_module_definition(
        "sklearn.neighbors._graph", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_KRadius_models"
    )

    _process_module_definition(
        "sklearn.neighbors._kde", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors.kde", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors._lof", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors.lof", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors._nca", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors._nearest_centroid", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors.nearest_centroid", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors._regression", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_KRadius_models"
    )

    _process_module_definition(
        "sklearn.neighbors.regression", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_KRadius_models"
    )

    _process_module_definition(
        "sklearn.neighbors._unsupervised", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "sklearn.neighbors.unsupervised", "newrelic.hooks.mlmodel_sklearn", "instrument_sklearn_neighbors_models"
    )

    _process_module_definition(
        "rest_framework.views", "newrelic.hooks.component_djangorestframework", "instrument_rest_framework_views"
    )
    _process_module_definition(
        "rest_framework.decorators",
        "newrelic.hooks.component_djangorestframework",
        "instrument_rest_framework_decorators",
    )

    _process_module_definition("celery.task.base", "newrelic.hooks.application_celery", "instrument_celery_app_task")
    _process_module_definition("celery.app.task", "newrelic.hooks.application_celery", "instrument_celery_app_task")
    _process_module_definition("celery.app.trace", "newrelic.hooks.application_celery", "instrument_celery_app_trace")
    _process_module_definition("celery.worker", "newrelic.hooks.application_celery", "instrument_celery_worker")
    _process_module_definition(
        "celery.concurrency.processes", "newrelic.hooks.application_celery", "instrument_celery_worker"
    )
    _process_module_definition(
        "celery.concurrency.prefork", "newrelic.hooks.application_celery", "instrument_celery_worker"
    )

    _process_module_definition("celery.app.base", "newrelic.hooks.application_celery", "instrument_celery_app_base")
    _process_module_definition("billiard.pool", "newrelic.hooks.application_celery", "instrument_billiard_pool")

    _process_module_definition("flup.server.cgi", "newrelic.hooks.adapter_flup", "instrument_flup_server_cgi")
    _process_module_definition("flup.server.ajp_base", "newrelic.hooks.adapter_flup", "instrument_flup_server_ajp_base")
    _process_module_definition(
        "flup.server.fcgi_base", "newrelic.hooks.adapter_flup", "instrument_flup_server_fcgi_base"
    )
    _process_module_definition(
        "flup.server.scgi_base", "newrelic.hooks.adapter_flup", "instrument_flup_server_scgi_base"
    )

    _process_module_definition("meinheld.server", "newrelic.hooks.adapter_meinheld", "instrument_meinheld_server")

    _process_module_definition("waitress.server", "newrelic.hooks.adapter_waitress", "instrument_waitress_server")

    _process_module_definition("gevent.wsgi", "newrelic.hooks.adapter_gevent", "instrument_gevent_wsgi")
    _process_module_definition("gevent.pywsgi", "newrelic.hooks.adapter_gevent", "instrument_gevent_pywsgi")

    _process_module_definition(
        "wsgiref.simple_server", "newrelic.hooks.adapter_wsgiref", "instrument_wsgiref_simple_server"
    )

    _process_module_definition(
        "cherrypy.wsgiserver", "newrelic.hooks.adapter_cherrypy", "instrument_cherrypy_wsgiserver"
    )

    _process_module_definition("cheroot.wsgi", "newrelic.hooks.adapter_cheroot", "instrument_cheroot_wsgiserver")

    _process_module_definition("pyramid.router", "newrelic.hooks.framework_pyramid", "instrument_pyramid_router")
    _process_module_definition("pyramid.config", "newrelic.hooks.framework_pyramid", "instrument_pyramid_config_views")
    _process_module_definition(
        "pyramid.config.views", "newrelic.hooks.framework_pyramid", "instrument_pyramid_config_views"
    )
    _process_module_definition(
        "pyramid.config.tweens", "newrelic.hooks.framework_pyramid", "instrument_pyramid_config_tweens"
    )

    _process_module_definition("cornice.service", "newrelic.hooks.component_cornice", "instrument_cornice_service")

    _process_module_definition("gevent.monkey", "newrelic.hooks.coroutines_gevent", "instrument_gevent_monkey")

    _process_module_definition("thrift.transport.TSocket", "newrelic.hooks.external_thrift")

    _process_module_definition("gearman.client", "newrelic.hooks.application_gearman", "instrument_gearman_client")
    _process_module_definition(
        "gearman.connection_manager", "newrelic.hooks.application_gearman", "instrument_gearman_connection_manager"
    )
    _process_module_definition("gearman.worker", "newrelic.hooks.application_gearman", "instrument_gearman_worker")

    _process_module_definition(
        "aiobotocore.client", "newrelic.hooks.external_aiobotocore", "instrument_aiobotocore_client"
    )

    _process_module_definition(
        "aiobotocore.endpoint", "newrelic.hooks.external_aiobotocore", "instrument_aiobotocore_endpoint"
    )

    _process_module_definition("botocore.endpoint", "newrelic.hooks.external_botocore", "instrument_botocore_endpoint")
    _process_module_definition("botocore.client", "newrelic.hooks.external_botocore", "instrument_botocore_client")

    _process_module_definition(
        "s3transfer.futures", "newrelic.hooks.external_s3transfer", "instrument_s3transfer_futures"
    )

    _process_module_definition(
        "tornado.httpserver", "newrelic.hooks.framework_tornado", "instrument_tornado_httpserver"
    )
    _process_module_definition("tornado.httputil", "newrelic.hooks.framework_tornado", "instrument_tornado_httputil")
    _process_module_definition(
        "tornado.httpclient", "newrelic.hooks.framework_tornado", "instrument_tornado_httpclient"
    )
    _process_module_definition("tornado.routing", "newrelic.hooks.framework_tornado", "instrument_tornado_routing")
    _process_module_definition("tornado.web", "newrelic.hooks.framework_tornado", "instrument_tornado_web")
    _process_module_definition(
        "azure.functions._http", "newrelic.hooks.framework_azurefunctions", "instrument_azure_function__http"
    )
    _process_module_definition(
        "azure_functions_worker.dispatcher",
        "newrelic.hooks.framework_azurefunctions",
        "instrument_azure_functions_worker_dispatcher",
    )


def _process_module_entry_points():
    try:
        # importlib.metadata was introduced into the standard library starting in Python 3.8.
        from importlib.metadata import entry_points
    except ImportError:
        try:
            # importlib_metadata is a backport library installable from PyPI.
            from importlib_metadata import entry_points
        except ImportError:
            try:
                # Fallback to pkg_resources, which is available in older versions of setuptools.
                from pkg_resources import iter_entry_points as entry_points
            except ImportError:
                return

    group = "newrelic.hooks"

    try:
        # group kwarg was only added to importlib.metadata.entry_points in Python 3.10.
        _entry_points = entry_points(group=group)
    except TypeError:
        # Grab entire entry_points dictionary and select group from it.
        _entry_points = entry_points().get(group, ())

    for entrypoint in _entry_points:
        target = entrypoint.name

        if target in _module_import_hook_registry:
            continue

        module = entrypoint.module_name

        if entrypoint.attrs:
            function = ".".join(entrypoint.attrs)
        else:
            function = "instrument"

        _process_module_definition(target, module, function)


_instrumentation_done = False


def _reset_instrumentation_done():
    global _instrumentation_done
    _instrumentation_done = False


def _setup_instrumentation():
    global _instrumentation_done

    if _instrumentation_done:
        return

    _instrumentation_done = True

    _process_module_configuration()
    _process_module_entry_points()
    _process_trace_cache_import_hooks()
    _process_module_builtin_defaults()

    _process_wsgi_application_configuration()
    _process_background_task_configuration()

    _process_database_trace_configuration()
    _process_external_trace_configuration()
    _process_function_trace_configuration()
    _process_generator_trace_configuration()
    _process_profile_trace_configuration()
    _process_memcache_trace_configuration()

    _process_transaction_name_configuration()

    _process_error_trace_configuration()

    _process_data_source_configuration()

    _process_function_profile_configuration()


def _setup_extensions():
    try:
        # importlib.metadata was introduced into the standard library starting in Python 3.8.
        from importlib.metadata import entry_points
    except ImportError:
        try:
            # importlib_metadata is a backport library installable from PyPI.
            from importlib_metadata import entry_points
        except ImportError:
            try:
                # Fallback to pkg_resources, which is available in older versions of setuptools.
                from pkg_resources import iter_entry_points as entry_points
            except ImportError:
                return

    group = "newrelic.extension"

    try:
        # group kwarg was only added to importlib.metadata.entry_points in Python 3.10.
        _entry_points = entry_points(group=group)
    except TypeError:
        # Grab entire entry_points dictionary and select group from it.
        _entry_points = entry_points().get(group, ())

    for entrypoint in _entry_points:
        __import__(entrypoint.module_name)
        module = sys.modules[entrypoint.module_name]
        module.initialize()


_console = None


def _startup_agent_console():
    global _console

    if _console:
        return

    _console = newrelic.console.ConnectionManager(_settings.console.listener_socket)


def _setup_agent_console():
    if _settings.console.listener_socket:
        newrelic.core.agent.Agent.run_on_startup(_startup_agent_console)


agent_control_health_thread = threading.Thread(
    name="Agent-Control-Health-Main-Thread", target=agent_control_healthcheck_loop
)
agent_control_health_thread.daemon = True


def _setup_agent_control_health():
    if agent_control_health_thread.is_alive():
        return

    try:
        if agent_control_health.health_check_enabled:
            agent_control_health_thread.start()
    except Exception:
        _logger.warning("Unable to start Agent Control health check thread. Health checks will not be enabled.")


def initialize(config_file=None, environment=None, ignore_errors=None, log_file=None, log_level=None):
    agent_control_health.start_time_unix_nano = time.time_ns()

    if config_file is None:
        config_file = os.environ.get("NEW_RELIC_CONFIG_FILE", None)

    if environment is None:
        environment = os.environ.get("NEW_RELIC_ENVIRONMENT", None)

    if ignore_errors is None:
        ignore_errors = newrelic.core.config._environ_as_bool("NEW_RELIC_IGNORE_STARTUP_ERRORS", True)

    _load_configuration(config_file, environment, ignore_errors, log_file, log_level)

    _setup_agent_control_health()

    if _settings.monitor_mode:
        if not _settings.license_key:
            agent_control_health.set_health_status(HealthStatus.MISSING_LICENSE.value)

    if _settings.monitor_mode or _settings.developer_mode:
        _settings.enabled = True
        _setup_instrumentation()
        _setup_data_source()
        _setup_extensions()
        _setup_agent_console()
    else:
        _settings.enabled = False
        agent_control_health.set_health_status(HealthStatus.AGENT_DISABLED.value)


def filter_app_factory(app, global_conf, config_file, environment=None):
    initialize(config_file, environment)
    return newrelic.api.wsgi_application.WSGIApplicationWrapper(app)
