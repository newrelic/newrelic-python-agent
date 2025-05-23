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

import json
import logging
import re
import warnings
from traceback import format_exception

from newrelic.api.application import application_instance
from newrelic.api.time_trace import get_linking_metadata
from newrelic.api.transaction import current_transaction, record_log_event
from newrelic.common import agent_http
from newrelic.common.encoding_utils import json_encode
from newrelic.common.object_names import parse_exc_info
from newrelic.core.attribute import truncate
from newrelic.core.config import global_settings, is_expected_error


def safe_json_encode(obj, ignore_string_types=False, **kwargs):
    # Performs the same operation as json_encode but replaces unserializable objects with a string containing their class name.
    # If ignore_string_types is True, do not encode string types further.
    # Currently used for safely encoding logging attributes.

    if ignore_string_types and isinstance(obj, (str, bytes)):
        return obj

    # Attempt to run through JSON serialization
    try:
        return json_encode(obj, **kwargs)
    except Exception:
        pass

    # If JSON serialization fails then return a repr
    try:
        return repr(obj)
    except Exception:
        # If repr fails then default to an unprinatable object name
        return f"<unprintable {type(obj).__name__} object>"


class NewRelicContextFormatter(logging.Formatter):
    DEFAULT_LOG_RECORD_KEYS = frozenset(set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {"message"})

    def __init__(self, *args, **kwargs):
        """
        :param Optional[int] stack_trace_limit:
            Specifies the maximum number of frames to include for stack traces.
            Defaults to `0` to suppress stack traces.
            Setting this to `None` will make it so all available frames are included.
        """
        stack_trace_limit = kwargs.pop("stack_trace_limit", 0)

        if stack_trace_limit is not None:
            if not isinstance(stack_trace_limit, int):
                raise TypeError("stack_trace_limit must be None or a non-negative integer")
            if stack_trace_limit < 0:
                raise ValueError("stack_trace_limit must be None or a non-negative integer")
        self._stack_trace_limit = stack_trace_limit

        super().__init__(*args, **kwargs)

    @classmethod
    def format_exc_info(cls, exc_info, stack_trace_limit=0):
        _, _, fullnames, message = parse_exc_info(exc_info)
        fullname = fullnames[0]

        formatted = {"error.class": fullname, "error.message": message}

        expected = is_expected_error(exc_info)
        if expected is not None:
            formatted["error.expected"] = expected

        if stack_trace_limit is None or stack_trace_limit > 0:
            if exc_info[2] is not None:
                stack_trace = "".join(format_exception(*exc_info, limit=stack_trace_limit)) or None
            else:
                stack_trace = None
            formatted["error.stack_trace"] = stack_trace

        return formatted

    @classmethod
    def log_record_to_dict(cls, record, stack_trace_limit=0):
        output = {
            "timestamp": int(record.created * 1000),
            "message": record.getMessage(),
            "log.level": record.levelname,
            "logger.name": record.name,
            "thread.id": record.thread,
            "thread.name": record.threadName,
            "process.id": record.process,
            "process.name": record.processName,
            "file.name": record.pathname,
            "line.number": record.lineno,
        }
        output.update(get_linking_metadata())

        DEFAULT_LOG_RECORD_KEYS = cls.DEFAULT_LOG_RECORD_KEYS
        # If any keys are present in record that aren't in the default,
        # add them to the output record.
        keys_to_add = set(record.__dict__.keys()) - DEFAULT_LOG_RECORD_KEYS
        for key in keys_to_add:
            output[f"extra.{key}"] = getattr(record, key)

        if record.exc_info:
            output.update(cls.format_exc_info(record.exc_info, stack_trace_limit))

        return output

    def format(self, record):
        return json.dumps(
            self.log_record_to_dict(record, self._stack_trace_limit), default=safe_json_encode, separators=(",", ":")
        )


# Export class methods as top level functions for compatibility
log_record_to_dict = NewRelicContextFormatter.log_record_to_dict
format_exc_info = NewRelicContextFormatter.format_exc_info


class NewRelicLogForwardingHandler(logging.Handler):
    IGNORED_LOG_RECORD_KEYS = {"message", "msg"}

    def emit(self, record):
        try:
            nr = None
            transaction = current_transaction()
            # Retrieve settings
            if transaction:
                settings = transaction.settings
                nr = transaction
            else:
                application = application_instance(activate=False)
                if application and application.enabled:
                    nr = application
                    settings = application.settings
                else:
                    # If no settings have been found, fallback to global settings
                    settings = global_settings()

            # If logging is enabled and the application or transaction is not None.
            if settings and settings.application_logging.enabled and nr:
                level_name = str(getattr(record, "levelname", "UNKNOWN"))
                if settings.application_logging.metrics.enabled:
                    nr.record_custom_metric("Logging/lines", {"count": 1})
                    nr.record_custom_metric(f"Logging/lines/{level_name}", {"count": 1})

                if settings.application_logging.forwarding.enabled:
                    if self.formatter:
                        # Formatter supplied, allow log records to be formatted into a string
                        message = self.format(record)
                    else:
                        # No formatter supplied, attempt to handle dict log records
                        message = record.msg
                        if not isinstance(message, dict):
                            # Allow python to convert the message to a string and template it with args.
                            message = record.getMessage()

                    # Grab and filter context attributes from log record
                    context_attrs = self.filter_record_attributes(record)

                    record_log_event(
                        message=message,
                        level=level_name,
                        timestamp=int(record.created * 1000),
                        attributes=context_attrs,
                    )
        except RecursionError:  # Emulates behavior of CPython.
            raise
        except Exception:
            self.handleError(record)

    @classmethod
    def filter_record_attributes(cls, record):
        record_attrs = vars(record)
        return {k: record_attrs[k] for k in record_attrs if k not in cls.IGNORED_LOG_RECORD_KEYS}


class NewRelicLogHandler(logging.Handler):
    """
    Deprecated: Please use NewRelicLogForwardingHandler instead.
    This is an experimental log handler provided by the community. Use with caution.
    """

    PATH = "/log/v1"

    def __init__(
        self,
        level=logging.INFO,
        license_key=None,
        host=None,
        port=443,
        proxy_scheme=None,
        proxy_host=None,
        proxy_user=None,
        proxy_pass=None,
        timeout=None,
        ca_bundle_path=None,
        disable_certificate_validation=False,
    ):
        warnings.warn(
            "The contributed NewRelicLogHandler has been superseded by automatic instrumentation for "
            "logging in the standard lib. If for some reason you need to manually configure a handler, "
            "please use newrelic.api.log.NewRelicLogForwardingHandler to take advantage of all the "
            "features included in application log forwarding such as proper batching.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(level=level)
        self.license_key = license_key or self.settings.license_key
        self.host = host or self.settings.host or self.default_host(self.license_key)

        self.client = agent_http.HttpClient(
            host=host,
            port=port,
            proxy_scheme=proxy_scheme,
            proxy_host=proxy_host,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            timeout=timeout,
            ca_bundle_path=ca_bundle_path,
            disable_certificate_validation=disable_certificate_validation,
        )

        self.setFormatter(NewRelicContextFormatter())

    @property
    def settings(self):
        transaction = current_transaction()
        if transaction:
            return transaction.settings
        return global_settings()

    def emit(self, record):
        try:
            headers = {"Api-Key": self.license_key or "", "Content-Type": "application/json"}
            payload = self.format(record).encode("utf-8")
            with self.client:
                status_code, response = self.client.send_request(path=self.PATH, headers=headers, payload=payload)
                if status_code < 200 or status_code >= 300:
                    raise RuntimeError(
                        f"An unexpected HTTP response of {status_code!r} was received for request made to https://{self.client._host}:{int(self.client._port)}{self.PATH}.The response payload for the request was {truncate(response.decode('utf-8'), 1024)!r}. If this issue persists then please report this problem to New Relic support for further investigation."
                    )

        except Exception:
            self.handleError(record)

    def default_host(self, license_key):
        if not license_key:
            return "log-api.newrelic.com"

        region_aware_match = re.match("^(.+?)x", license_key)
        if not region_aware_match:
            return "log-api.newrelic.com"

        region = region_aware_match.group(1)
        host = f"log-api.{region}.newrelic.com"
        return host
