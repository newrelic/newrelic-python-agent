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
from logging import Formatter, LogRecord

from newrelic.api.time_trace import get_linking_metadata
from newrelic.common.object_names import parse_exc_info
from newrelic.core.config import is_expected_error


def format_exc_info(exc_info):
    _, _, fullnames, message = parse_exc_info(exc_info)
    fullname = fullnames[0]

    formatted = {
        "error.class": fullname,
        "error.message": message,
    }

    expected = is_expected_error(exc_info)
    if expected is not None:
        formatted["error.expected"] = expected

    return formatted


class NewRelicContextFormatter(Formatter):
    DEFAULT_LOG_RECORD_KEYS = frozenset(vars(LogRecord("", 0, "", 0, "", (), None)))

    def __init__(self, *args, **kwargs):
        super(NewRelicContextFormatter, self).__init__()

    @classmethod
    def log_record_to_dict(cls, record):
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
        if len(record.__dict__) > len(DEFAULT_LOG_RECORD_KEYS):
            for key in record.__dict__:
                if key not in DEFAULT_LOG_RECORD_KEYS:
                    output["extra." + key] = getattr(record, key)

        if record.exc_info:
            output.update(format_exc_info(record.exc_info))

        return output

    def format(self, record):
        def safe_str(object, *args, **kwargs):
            """Convert object to str, catching any errors raised."""
            try:
                return str(object, *args, **kwargs)
            except:
                return "<unprintable %s object>" % type(object).__name__

        return json.dumps(self.log_record_to_dict(record), default=safe_str, separators=(",", ":"))
