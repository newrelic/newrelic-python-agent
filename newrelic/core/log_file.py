"""This module sets up use of the Python logging module by the agent. As we
don't want to rely exclusively on user having configured the logging module
themselves to capture any logged output we attach our own log file when
enabled from agent configuration. We also provide ability to fallback to
using stdout or stderr.

"""

import os
import sys
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

class FilteredStreamHandler(logging.StreamHandler):
    def emit(self, record):
        if len(logging.root.handlers) != 0:
            return

        # Make sure we suppress any logging messages coming from third
        # party packages we have bundled which use the module name as
        # the logger name. The 'requests' module in particular is very
        # verbose with its INFO messages when creating new socket
        # connections in its pooling mechanism.

        if not record.name.startswith('newrelic.lib'):
            return logging.StreamHandler.emit(self, record)

class FilteredFileHandler(logging.FileHandler):
    def emit(self, record):
        # Make sure we suppress any logging messages coming from third
        # party packages we have bundled which use the module name as
        # the logger name. The 'requests' module in particular is very
        # verbose with its INFO messages when creating new socket
        # connections in its pooling mechanism.

        if not record.name.startswith('newrelic.lib'):
            return logging.FileHandler.emit(self, record)

# This is to filter out the overly verbose log messages at INFO level
# made by the urllib3 module embedded in the bundled requests module.
# this possibly negates the need for the above custom handlers now.

class RequestsConnectionFilter(logging.Filter):
    def filter(self, record):
        return False

_requests_logger = logging.getLogger(
    'newrelic.lib.requests.packages.urllib3.connectionpool')
_requests_logger.addFilter(RequestsConnectionFilter())

_initialized = False

def initialize():
    global _initialized

    if _initialized:
        return

    _lock.acquire()
    try:
        settings = newrelic.core.config.global_settings()

        if settings.log_file == 'stdout':
            #handler = FilteredStreamHandler(sys.stdout)
            handler = logging.StreamHandler(sys.stdout)

            formatter = logging.Formatter(_LOG_FORMAT)
            handler.setFormatter(formatter)

            _agent_logger.addHandler(handler)
            _agent_logger.setLevel(settings.log_level)

            _agent_logger.debug('Initializing Python agent stdout logging.')

        elif settings.log_file == 'stderr':
            #handler = FilteredStreamHandler(sys.stderr)
            handler = logging.StreamHandler(sys.stderr)

            formatter = logging.Formatter(_LOG_FORMAT)
            handler.setFormatter(formatter)

            _agent_logger.addHandler(handler)
            _agent_logger.setLevel(settings.log_level)

            _agent_logger.debug('Initializing Python agent stderr logging.')

        elif settings.log_file:
            try:
                #handler = FilteredFileHandler(settings.log_file)
                handler = logging.FileHandler(settings.log_file)

                formatter = logging.Formatter(_LOG_FORMAT)
                handler.setFormatter(formatter)

                _agent_logger.addHandler(handler)
                _agent_logger.setLevel(settings.log_level)

                _agent_logger.debug('Initializing Python agent logging.')
                _agent_logger.debug('Log file "%s".' % settings.log_file)

            except:
                handler = FilteredStreamHandler(sys.stderr)

                formatter = logging.Formatter(_LOG_FORMAT)
                handler.setFormatter(formatter)

                _agent_logger.addHandler(handler)
                _agent_logger.setLevel(settings.log_level)

                _agent_logger.exception('Unable to create log file "%s".' %
                                        settings.log_file)

                _agent_logger.debug('Initializing Python agent stderr logging.')
    finally:
        _lock.release()

    _initialized = True
