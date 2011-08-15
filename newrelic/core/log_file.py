import logging
import threading

import newrelic.core.config

_lock = threading.Lock()
_agent_logger = None
_agent_handler = None

class _NullHandler(logging.Handler):
    def emit(self, record):
        pass

_LOG_FORMAT = '%(asctime)s (%(process)d/%(threadName)s) ' \
              '%(name)s %(levelname)s - %(message)s'

def initialize():
    global _agent_logger

    if _agent_logger:
        return

    _lock.acquire()
    try:
        if not _agent_logger:
            _agent_logger = logging.getLogger('newrelic')

            settings = newrelic.core.config.global_settings()

            if settings.log_file:
                handler = logging.FileHandler(settings.log_file)

                formatter = logging.Formatter(_LOG_FORMAT)
                handler.setFormatter(formatter)

                _agent_logger.addHandler(handler)
                _agent_logger.setLevel(settings.log_level)

                _agent_logger.info('New Relic log file is "%s"' %
                                   settings.log_file)
            else:
                handler = _NullHandler()

                _agent_logger.addHandler(handler)
    finally:
        _lock.release()
