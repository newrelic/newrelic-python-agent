import os
import logging

_agent_mode = os.environ.get('NEWRELIC_AGENT_MODE', '').lower()

LOG_ERROR = logging.ERROR
LOG_WARNING = logging.WARNING
LOG_INFO = logging.INFO
LOG_VERBOSE = logging.INFO
LOG_DEBUG = logging.DEBUG
LOG_VERBOSEDEBUG = logging.DEBUG

_logger = logging.getLogger('newrelic')

# TODO This needs to go away when convert everything over.

def log(level, message):
    if _logger.isEnabledFor(level):
        _logger._log(level, message, args=())

def log_exception(level, message, *args):
    if _logger.isEnabledFor(level):
        _logger._log(level, message, args=(), exc_info=args)

if not _agent_mode in ('julunggul',):
    import _newrelic

    log = _newrelic.log
    log_exception = _newrelic.log_exception

    LOG_ERROR = _newrelic.LOG_ERROR
    LOG_WARNING = _newrelic.LOG_WARNING
    LOG_INFO = _newrelic.LOG_INFO
    LOG_VERBOSE = _newrelic.LOG_VERBOSE
    LOG_DEBUG = _newrelic.LOG_DEBUG
    LOG_VERBOSEDEBUG = _newrelic.LOG_VERBOSEDEBUG
