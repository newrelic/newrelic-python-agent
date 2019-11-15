import json
import logging
from newrelic.api.time_trace import get_linking_metadata


class NewRelicContextFormatter(logging.Formatter):
    def format(self, record):
        output = {
            "timestamp": int(record.created * 1000),
            "message": record.getMessage(),
            "log.level": record.levelname,
            "logger.name": record.name,
            "thread.id": record.thread,
            "thread.name": record.threadName,
            "file.name": record.pathname,
            "line.number": record.lineno,
        }
        output.update(get_linking_metadata())
        return json.dumps(output)
