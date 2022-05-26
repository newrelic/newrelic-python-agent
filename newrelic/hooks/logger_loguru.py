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

from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction, record_log_event
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.config import global_settings
from newrelic.hooks.logger_logging import add_nr_linking_metadata

_logger = logging.getLogger(__name__) 

def loguru_version():
    from loguru import __version__
    return tuple(int(x) for x in __version__.split("."))


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
                transaction.record_custom_metric("Logging/lines/%s" % level_name, {"count": 1})
            else:
                application = application_instance(activate=False)
                if application and application.enabled:
                    application.record_custom_metric("Logging/lines", {"count": 1})
                    application.record_custom_metric("Logging/lines/%s" % level_name, {"count": 1})
            
        if settings.application_logging.forwarding and settings.application_logging.forwarding.enabled:
            try:
                record_log_event(message, level_name, int(record["time"].timestamp()))
            except Exception:
                pass


def bind_log(level_id, static_level_no, from_decorator, options, message, args, kwargs):
    assert len(options) == 9  # Assert the options signature we expect
    return level_id, static_level_no, from_decorator, list(options), message, args, kwargs


def wrap_log(wrapped, instance, args, kwargs):
    try:
        level_id, static_level_no, from_decorator, options, message, subargs, subkwargs = bind_log(*args, **kwargs)
        options[-2] = nr_log_patcher(options[-2])
    except Exception as e:
        _logger.debug("Exception in loguru handling: %s" % str(e))
        return wrapped(*args, **kwargs)
    else:
        return wrapped(level_id, static_level_no, from_decorator, options, message, subargs, subkwargs)


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

    if loguru_version() > (0, 6, 0):
        if original_patcher is not None:
            patchers = [p for p in original_patcher]  # Consumer iterable into list so we can modify
            # Wipe out reference so patchers aren't called twice, as the framework will handle calling other patchers.
            original_patcher = None
        else:
            patchers = []

        patchers.append(_nr_log_patcher)
        return patchers
    else:
        return _nr_log_patcher


def wrap_Logger_init(wrapped, instance, args, kwargs):
    logger = wrapped(*args, **kwargs)
    patch_loguru_logger(logger)
    return logger


def patch_loguru_logger(logger):
    if hasattr(logger, "_core") and not hasattr(logger._core, "_nr_instrumented"):
        core = logger._core
        logger.add(_nr_log_forwarder, format="{message}")
        logger._core._nr_instrumented = True


def instrument_loguru_logger(module):
    if hasattr(module, "Logger"):
        wrap_function_wrapper(module, "Logger.__init__", wrap_Logger_init)
        if hasattr(module.Logger, "_log"):
            wrap_function_wrapper(module, "Logger._log", wrap_log)


def instrument_loguru(module):
    if hasattr(module, "logger"):
        if hasattr(module.logger, "_core") and not hasattr(module.logger._core, "_nr_instrumented"):
            patch_loguru_logger(module.logger)
