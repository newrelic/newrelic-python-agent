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

import logging
import sys

from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction, record_log_event
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings
from newrelic.hooks.logger_logging import add_nr_linking_metadata

_logger = logging.getLogger(__name__)

IS_PYPY = hasattr(sys, "pypy_version_info")
LOGURU_FILTERED_RECORD_ATTRS = {"extra", "message", "time", "level", "_nr_original_message", "record"}
ALLOWED_LOGURU_OPTIONS_LENGTHS = frozenset((8, 9))


def _filter_record_attributes(record):
    attrs = {k: v for k, v in record.items() if k not in LOGURU_FILTERED_RECORD_ATTRS}
    extra_attrs = dict(record.get("extra", {}))
    attrs.update({f"extra.{k}": v for k, v in extra_attrs.items()})
    return attrs


def _nr_log_forwarder(message_instance):
    transaction = current_transaction()
    record = message_instance.record
    message = record.get("_nr_original_message", record["message"])

    if transaction:
        settings = transaction.settings
    else:
        settings = global_settings()

    # Return early if application logging not enabled
    if settings and settings.application_logging and settings.application_logging.enabled:
        level = record["level"]
        level_name = "UNKNOWN" if not level else (level.name or "UNKNOWN")

        if settings.application_logging.metrics and settings.application_logging.metrics.enabled:
            if transaction:
                transaction.record_custom_metric("Logging/lines", {"count": 1})
                transaction.record_custom_metric(f"Logging/lines/{level_name}", {"count": 1})
            else:
                application = application_instance(activate=False)
                if application and application.enabled:
                    application.record_custom_metric("Logging/lines", {"count": 1})
                    application.record_custom_metric(f"Logging/lines/{level_name}", {"count": 1})

        if settings.application_logging.forwarding and settings.application_logging.forwarding.enabled:
            attrs = _filter_record_attributes(record)

            try:
                time = record.get("time", None)
                if time:
                    time = int(time.timestamp() * 1000)
                record_log_event(message, level_name, time, attributes=attrs)
            except Exception:
                pass


def wrap_log(wrapped, instance, args, kwargs):
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        options = bound_args["options"] = list(bound_args["options"])
        if len(options) not in ALLOWED_LOGURU_OPTIONS_LENGTHS:  # Assert the options signature we expect
            raise RuntimeError("Unexpected number of options in loguru call. Instrumentation may be out of date.")

        options[-2] = nr_log_patcher(options[-2])
        # Loguru looks into the stack trace to find the caller's module and function names.
        # options[1] tells loguru how far up to look in the stack trace to find the caller.
        # Because wrap_log is an extra call in the stack trace, loguru needs to look 1 level higher.
        if not IS_PYPY:
            options[1] += 1
        else:
            # PyPy inspection requires an additional frame of offset, as the wrapt internals seem to
            # add another frame on PyPy but not on CPython.
            options[1] += 2

    except Exception as e:
        _logger.debug("Exception in loguru handling: %s", e)
        return wrapped(*args, **kwargs)
    else:
        return wrapped(**bound_args)


def nr_log_patcher(original_patcher=None):
    def _nr_log_patcher(record):
        if original_patcher:
            record = original_patcher(record)

        transaction = current_transaction()

        if transaction:
            settings = transaction.settings
        else:
            settings = global_settings()

        if settings and settings.application_logging and settings.application_logging.enabled:
            if settings.application_logging.local_decorating and settings.application_logging.local_decorating.enabled:
                record["_nr_original_message"] = message = record["message"]
                record["message"] = add_nr_linking_metadata(message)

    if original_patcher is not None:
        patchers = list(original_patcher)  # Consumer iterable into list so we can modify
        # Wipe out reference so patchers aren't called twice, as the framework will handle calling other patchers.
        original_patcher = None
    else:
        patchers = []

    patchers.append(_nr_log_patcher)
    return patchers


def wrap_Logger_init(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    patch_loguru_logger(instance)
    return result


def patch_loguru_logger(logger):
    if hasattr(logger, "_core"):
        if not hasattr(logger._core, "_nr_instrumented"):
            logger.add(_nr_log_forwarder, format="{message}")
            logger._core._nr_instrumented = True
    elif not hasattr(logger, "_nr_instrumented"):  # pragma: no cover
        for handler in logger._handlers.values():
            if handler._writer is _nr_log_forwarder:
                logger._nr_instrumented = True
                return

        logger.add(_nr_log_forwarder, format="{message}")
        logger._nr_instrumented = True


def instrument_loguru_logger(module):
    if hasattr(module, "Logger"):
        wrap_function_wrapper(module, "Logger.__init__", wrap_Logger_init)
        if hasattr(module.Logger, "_log"):
            wrap_function_wrapper(module, "Logger._log", wrap_log)


def instrument_loguru(module):
    if hasattr(module, "logger"):
        patch_loguru_logger(module.logger)
