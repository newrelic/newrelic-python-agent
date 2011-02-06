#vi: set sw=4 expandtab :

import _newrelic

LOG_ERROR = _newrelic.LOG_ERROR
LOG_INFO = _newrelic.LOG_INFO
LOG_WARNING = _newrelic.LOG_WARNING
LOG_VERBOSE = _newrelic.LOG_VERBOSE
LOG_DEBUG = _newrelic.LOG_DEBUG
LOG_VERBOSEDEBUG = _newrelic.LOG_VERBOSEDEBUG

log = _newrelic.log
settings = _newrelic.settings
application = _newrelic.application
transaction = _newrelic.transaction

WebTransaction = _newrelic.WebTransaction
BackgroundTask = _newrelic.BackgroundTask

from applications import initialize
from middleware import WSGIApplication
from decorators import (wsgi_application, function_trace, external_trace,
                        memcache_trace, database_trace)
