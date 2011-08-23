"""This module sets up use of the Python logging module by the agent. As we
don't want to rely exclusively on user having configured the logging module
themselves to capture any logged output we attach our own log file when
enabled from agent configuration.

"""

import logging
import threading

import newrelic.core.config

_lock = threading.Lock()

class _NullHandler(logging.Handler):
    def emit(self, record):
        pass

_agent_logger = None
_agent_logger = logging.getLogger('newrelic')
_agent_logger.addHandler(_NullHandler())

_LOG_FORMAT = '%(asctime)s (%(process)d/%(threadName)s) ' \
              '%(name)s %(levelname)s - %(message)s'

_initialized = False

def initialize():
    global _initialized

    if _initialized:
        return

    _lock.acquire()
    try:
        settings = newrelic.core.config.global_settings()

        if settings.log_file:
            handler = logging.FileHandler(settings.log_file)

            formatter = logging.Formatter(_LOG_FORMAT)
            handler.setFormatter(formatter)

            # TODO Have to check how log levels play out
            # when user also capturing in own log file. We
            # may not be able to set level on 'newrelic'
            # logger as that may be only place for user to
            # override it. We may need to separately set it
            # on each of our nested loggers, ie.,
            # 'newrelic.core', 'newrelic.api' and
            # 'newrelic.config'.

            _agent_logger.addHandler(handler)
            _agent_logger.setLevel(settings.log_level)

            _agent_logger.debug('Initializing Python agent logging.')
            _agent_logger.debug('Log file "%s".' % settings.log_file)
    finally:
        _lock.release()

    _initialized = True
