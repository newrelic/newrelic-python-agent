import threading

import _newrelic

LOG_ERROR = _newrelic.LOG_ERROR
LOG_INFO = _newrelic.LOG_INFO
LOG_WARNING = _newrelic.LOG_WARNING
LOG_VERBOSE = _newrelic.LOG_VERBOSE
LOG_DEBUG = _newrelic.LOG_DEBUG
LOG_VERBOSEDEBUG = _newrelic.LOG_VERBOSEDEBUG

settings = _newrelic.Settings()

_applications_lock = threading.RLock()
_applications = {}

def _Application(name, framework=None):
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

class _CallbackGenerator:

    def __init__(self, generator, callback):
        self.__generator = generator
        self.__callback = callback

    def __iter__(self):
        for item in self.__generator:
            yield item

    def close(self):
        if hasattr(self.__generator, 'close'):
            self.__generator.close()
        self.__callback()

class _ExecuteOnCompletion:

    def __init__(self, application, callable):
        self.__application = application
        self.__callable = callable

    def __call__(self, environ, start_response):
        transaction = self.__application.web_transaction(environ)
        transaction.__enter__()
        try:
            result = self.__callable(environ, start_response)
        except:
            transaction.__exit__()
            raise
        return _CallbackGenerator(result, transaction.__exit__)

def application_monitor(name, framework=None):
    application = _Application(name, framework)

    def decorator(callable):
        return _ExecuteOnCompletion(application, callable)

    return decorator

