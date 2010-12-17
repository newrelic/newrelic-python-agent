import threading

import _newrelic

LOG_ERROR = _newrelic.LOG_ERROR
LOG_INFO = _newrelic.LOG_INFO
LOG_WARNING = _newrelic.LOG_WARNING
LOG_VERBOSE = _newrelic.LOG_VERBOSE
LOG_DEBUG = _newrelic.LOG_DEBUG
LOG_VERBOSEDEBUG = _newrelic.LOG_VERBOSEDEBUG

_global_settings = _newrelic.GlobalSettings()

def GlobalSettings():
    return _global_settings

_applications_lock = threading.RLock()
_applications = {}

def Application(name, framework=None):
    # We ensure only single application object for a specific
    # name is created as it is the Python object and not the
    # internal agent client application instance that holds the
    # 'enabled' flag indicating whether monitoring for this
    # agent is being performed.

    _applications_lock.acquire()

    application = _applications.get(name, None)

    if application is None:
        application = _newrelic.Application(name, framework)
        _applications[name] = application

    _applications_lock.release()

    return application 
