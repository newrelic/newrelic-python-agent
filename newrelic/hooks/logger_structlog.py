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
import calendar
import time

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.transaction import current_transaction, record_log_event
from newrelic.core.config import global_settings
from newrelic.api.application import application_instance
from newrelic.hooks.logger_logging import add_nr_linking_metadata


def bind_add_log_level(logger, method_name, event_dict):
    return logger, method_name, event_dict


def wrap_add_log_level(wrapped, instance, args, kwargs):
    logger, method_name, event_dict = bind_add_log_level(*args, **kwargs)
    if method_name == "warn":
        method_name = "warning"

    method_name = method_name.upper()

    transaction = current_transaction()

    if transaction:
        settings = transaction.settings
    else:
        settings = global_settings()

    # Return early if application logging not enabled
    if settings and settings.application_logging and settings.application_logging.enabled:
        level_name = "UNKNOWN" if not method_name else (method_name or "UNKNOWN")
        message = event_dict["event"] #Structlog records are stored in an event dictionary where the log message key is "event"

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
                record_log_event(message, level_name, calendar.timegm(time.gmtime()))
            except Exception:
                pass

        if settings.application_logging.local_decorating and settings.application_logging.local_decorating.enabled:
            event_dict["_nr_original_message"] = message
            event_dict["event"] = add_nr_linking_metadata(message)

    return wrapped(*args, **kwargs)


def instrument_structlog__log_levels(module):
    if hasattr(module, "add_log_level"):
        wrap_function_wrapper(module, "add_log_level", wrap_add_log_level)
