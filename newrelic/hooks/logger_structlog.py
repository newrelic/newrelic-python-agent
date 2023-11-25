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

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.transaction import current_transaction, record_log_event
from newrelic.core.config import global_settings
from newrelic.api.application import application_instance
from newrelic.hooks.logger_logging import add_nr_linking_metadata
from newrelic.common.signature import bind_args


def normalize_level_name(method_name):
    # Look up level number for method name, using result to look up level name for that level number.
    # Convert result to upper case, and default to UNKNOWN in case of errors or missing values.
    try:
        from structlog._log_levels import _LEVEL_TO_NAME, _NAME_TO_LEVEL
        return _LEVEL_TO_NAME[_NAME_TO_LEVEL[method_name]].upper()
    except Exception:
        return "UNKNOWN"


def bind_process_event(method_name, event, event_kw):
    return method_name, event, event_kw


def wrap__process_event(wrapped, instance, args, kwargs):
    try:
        method_name, event, event_kw = bind_process_event(*args, **kwargs)
    except TypeError:
        return wrapped(*args, **kwargs)

    original_message = event  # Save original undecorated message

    transaction = current_transaction()

    if transaction:
        settings = transaction.settings
    else:
        settings = global_settings()

    # Return early if application logging not enabled
    if settings and settings.application_logging and settings.application_logging.enabled:
        if settings.application_logging.local_decorating and settings.application_logging.local_decorating.enabled:
            event = add_nr_linking_metadata(event)

        # Send log to processors for filtering, allowing any DropEvent exceptions that occur to prevent instrumentation from recording the log event.
        result = wrapped(method_name, event, event_kw)
        
        level_name = normalize_level_name(method_name)

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
                record_log_event(original_message, level_name)

            except Exception:
                pass

        # Return the result from wrapped after we've recorded the resulting log event.
        return result

    return wrapped(*args, **kwargs)


def wrap__find_first_app_frame_and_name(wrapped, instance, args, kwargs):
    try:
        bound_args = bind_args(wrapped, args, kwargs)
        if bound_args["additional_ignores"]:
            bound_args["additional_ignores"] = list(bound_args["additional_ignores"])
            bound_args["additional_ignores"].append("newrelic")
        else:
            bound_args["additional_ignores"] = ["newrelic"]
    except Exception:
        return wrapped(*args, **kwargs)

    return wrapped(**bound_args)


def instrument_structlog__base(module):
    if hasattr(module, "BoundLoggerBase") and hasattr(module.BoundLoggerBase, "_process_event"):
        wrap_function_wrapper(module, "BoundLoggerBase._process_event", wrap__process_event)


def instrument_structlog__frames(module):
    if hasattr(module, "_find_first_app_frame_and_name"):
        wrap_function_wrapper(module, "_find_first_app_frame_and_name", wrap__find_first_app_frame_and_name)
