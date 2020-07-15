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
import newrelic.packages.six as six
from logging import Formatter, LogRecord
from newrelic.api.time_trace import get_linking_metadata


def format_exc_info(exc_info):
    _, value, tb = exc_info

    module = value.__class__.__module__
    name = value.__class__.__name__

    if module:
        fullname = "{}.{}".format(module, name)
    else:
        fullname = name

    try:

        # Favor unicode in exception messages.

        message = six.text_type(value)

    except Exception:
        try:

            # If exception cannot be represented in unicode, this means
            # that it is a byte string encoded with an encoding
            # that is not compatible with the default system encoding.
            # So, just pass this byte string along.

            message = str(value)

        except Exception:
            message = "<unprintable %s object>" % type(value).__name__

    return {
        "error.class": fullname,
        "error.message": message,
    }


class NewRelicContextFormatter(Formatter):
    DEFAULT_LOG_RECORD_KEYS = frozenset(vars(LogRecord("", 0, "", 0, "", (), None)))

    def __init__(self, *args, **kwargs):
        super(NewRelicContextFormatter, self).__init__()

    def format(self, record):
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

        DEFAULT_LOG_RECORD_KEYS = self.DEFAULT_LOG_RECORD_KEYS
        if len(record.__dict__) > len(DEFAULT_LOG_RECORD_KEYS):
            for key in record.__dict__:
                if key not in DEFAULT_LOG_RECORD_KEYS:
                    try:
                        value = str(getattr(record, key))
                    except Exception:
                        continue

                    output["extra." + key] = value

        if record.exc_info:
            output.update(format_exc_info(record.exc_info))
        return json.dumps(output)
