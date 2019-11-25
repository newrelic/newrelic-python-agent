import json
import newrelic.packages.six as six
from logging import Formatter
from newrelic.api.time_trace import get_linking_metadata


def format_exc_info(exc_info):
    _, value, tb = exc_info

    module = value.__class__.__module__
    name = value.__class__.__name__

    if module:
        fullname = '{}.{}'.format(module, name)
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
            message = '<unprintable %s object>' % type(value).__name__

    return {
        "error.class": fullname,
        "error.message": message,
    }


class NewRelicContextFormatter(Formatter):
    def __init__(self):
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
        if record.exc_info:
            output.update(format_exc_info(record.exc_info))
        return json.dumps(output)
