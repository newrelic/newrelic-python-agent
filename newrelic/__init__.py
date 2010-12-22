import threading
import atexit
import types
import sys

import _newrelic

LOG_ERROR = _newrelic.LOG_ERROR
LOG_INFO = _newrelic.LOG_INFO
LOG_WARNING = _newrelic.LOG_WARNING
LOG_VERBOSE = _newrelic.LOG_VERBOSE
LOG_DEBUG = _newrelic.LOG_DEBUG
LOG_VERBOSEDEBUG = _newrelic.LOG_VERBOSEDEBUG

# Provide single instance of settings object as a convenience.

settings = _newrelic.Settings()

# We ensure only single application object for a specific name
# is created as it is the Python object and not the internal
# agent client application instance that holds the 'enabled'
# flag indicating whether monitoring for this agent is being
# performed. If allow multiple instances of the application
# object then disabling it in one will not disable any of the
# transactions triggered via another instance of the application
# for the same named application. We also force a harvest when
# first creating an instance of an application because the local
# daemon will not accept metrics the first time if it does not
# know about the application. This forced harvest primes it and
# ensures that it talks to RPM to get configuration so that when
# next harvest occurs it doesn't reject metrics data. This is
# especially important where process generating metrics is short
# lived.

_applications_lock = threading.RLock()
_applications = {}

def _Application(name, framework=None):

    _applications_lock.acquire()

    application = _applications.get(name, None)

    if application is None:
        application = _newrelic.Application(name, framework)
        _applications[name] = application
        _newrelic.harvest()

    _applications_lock.release()

    return application 

# A harvest will only normally be forced when all the
# application objects are destroyed. Because application objects
# are cached by above code then would only occur when Python is
# destroying all the loaded modules. Force a harvest of data
# when registered exit handlers are run. This should be before
# when modules are being destroyed and everything still in place
# in memory. Note that some hosting mechanisms, such as
# mod_python, make use of Python sub interpreters but exit
# callbacks are triggered within sub interpreters, only the main
# interpreter. Thus this will still not be called. If using
# mod_wsgi there is no problem as it explicitly triggers exit
# callbacks for sub interpreters even though Python itself does
# not do it.

atexit.register(_newrelic.harvest)

# Provide a WSGI middleware wrapper, usable as a decorator, for
# initiating a web transaction for each request and ensuring
# that timing is started and stopped appropriately. For WSGI
# comliant case the latter is quite tricky as need to attach it
# to when the 'close()' method of any generator returned by an
# WSGI application is called. Only way to do this is to wrap
# response from the WSGI application with a generator with it
# having a 'close()' method which in turn executes the wrapped
# generators 'close()' method when it exists and then executing
# and finalisation. Doing this defeats any optimisations
# possible through using 'wsgi.file_wrapper'. For mod_wsgi case
# rely on a specific back door in mod_wsgi which allows
# extraction of file object from 'wsgi.file_wrapper' instance as
# we rewrap the file object and create new 'wsgi.file_wrapper'.
# The 'close()' of the wrapped file object is then replaced
# rather than needing a new generator be created that stops
# 'wsgi.file_wrapper' from working.

class _ExitCallbackFile:

    def __init__(self, filelike, callback):
        self.__filelike = filelike
        self.__callback = callback

        if hasattr(self.__filelike, 'fileno'):
            self.fileno = self.__filelike.fileno
        if hasattr(self.__filelike, 'read'):
            self.read = self.__filelike.read
        if hasattr(self.__filelike, 'tell'):
            self.tell = self.__filelike.tell

    def close(self):
        try:
            if hasattr(self.__filelike, 'close'):
                self.__filelike.close()
        except:
            self.__callback(*sys.exc_info())
            raise
        finally:
            self.__callback(None, None, None)

class _ExitCallbackGenerator:

    def __init__(self, generator, callback):
        self.__generator = generator
        self.__callback = callback

    def __iter__(self):
        for item in self.__generator:
            yield item

    def close(self):
        try:
            if hasattr(self.__generator, 'close'):
                self.__generator.close()
        except:
            self.__callback(*sys.exc_info())
            raise
        finally:
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
            transaction.__exit__(*sys.exc_info())
            raise

        if str(type(result)).find("'mod_wsgi.Stream'") != -1 and \
                hasattr(result, 'file'):
            return environ['wsgi.file_wrapper'](
                    _ExitCallbackFile(result.file(), transaction.__exit__))
        else:
            return _ExitCallbackGenerator(result, transaction.__exit__)

def application_monitor(name, framework=None):
    application = _Application(name, framework)

    def decorator(callable):
        return _ExecuteOnCompletion(application, callable)

    return decorator
