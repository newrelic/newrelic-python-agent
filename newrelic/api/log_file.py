import logging

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
