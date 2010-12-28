# vi: set sw=4 expandtab :

import threading
import atexit
import types
import sys
import traceback
import os

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

def _Application(name):

    _applications_lock.acquire()

    application = _applications.get(name, None)

    if application is None:
        application = _newrelic.Application(name)
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

_context = threading.local()

def current_transaction():
    try:
        return _context.transactions[-1]
    except IndexError:
        raise RuntimeError('no active transaction')

class _ExitCallbackFile:

    def __init__(self, transaction, file):
        self.__transaction = transaction
        self.__file = file

        if hasattr(self.__file, 'fileno'):
            self.fileno = self.__file.fileno
        if hasattr(self.__file, 'read'):
            self.read = self.__file.read
        if hasattr(self.__file, 'tell'):
            self.tell = self.__file.tell

    def close(self):
        try:
            if hasattr(self.__file, 'close'):
                self.__file.close()
        except:
            #sys.setprofile(None)
            self.__transaction.__exit__(*sys.exc_info())
            raise
        else:
            #sys.setprofile(None)
            self.__transaction.__exit__(None, None, None)
        finally:
            _context.transactions.pop()

class _ExitCallbackGenerator:

    def __init__(self, transaction, generator):
        self.__transaction = transaction
        self.__generator = generator

    def __iter__(self):
        for item in self.__generator:
            yield item

    def close(self):
        try:
            if hasattr(self.__generator, 'close'):
                self.__generator.close()
        except:
            #sys.setprofile(None)
            self.__transaction.__exit__(*sys.exc_info())
            raise
        else:
            #sys.setprofile(None)
            self.__transaction.__exit__(None, None, None)
        finally:
            _context.transactions.pop()

class _ExecuteOnCompletion:

    def __init__(self, application, callable):
        self.__application = application
        self.__callable = callable

    def __call__(self, environ, start_response):
        transaction = self.__application.web_transaction(environ)

        try:
            _context.transactions.append(transaction)
        except AttributeError:
            _context.transactions = [transaction]

        transaction.__enter__()
        #sys.setprofile(profiler)

        import time
        transaction.custom_parameters['time'] = time.time()

        def _start_response(status, response_headers, exc_info=None):
            transaction.response_code = int(status.split(' ')[0])
            return start_response(status, response_headers, exc_info)

        try:
            result = self.__callable(environ, _start_response)
        except:
            sys.setprofile(None)
            transaction.__exit__(*sys.exc_info())
            _context.transactions.pop()
            raise

        if str(type(result)).find("'mod_wsgi.Stream'") != -1 and \
                hasattr(result, 'file'):
            return environ['wsgi.file_wrapper'](
                    _ExitCallbackFile(transaction, result.file()))
        else:
            return _ExitCallbackGenerator(transaction, result)

def web_transaction(name):
    application = _Application(name)

    def decorator(callable):
        return _ExecuteOnCompletion(application, callable)

    return decorator

# Provide decorators for transaction traces which ensure sub
# timing is started and stopped appropriatey in all situations.
# Note that these stop timing on exit from the wrapped callable.
# If the result is a generator which is then consumed in outer
# scope, that consumption doesn't count towards the time.

def _qualified_name(callable):
    if hasattr(callable, 'im_class'):
        return '%s:%s.%s' % (callable.im_class.__module__,
                callable.im_class.__name__, callable.__name__)
    elif hasattr(callable, '__module__'):
        return '%s:%s' % (callable.__module__, callable.__name__)
    else:
        return callable.__name__

def function_trace(name=None, inherit=False):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            try:
                transaction = _context.transactions[-1]
            except IndexError:
                return callable(*args, **kwargs)

            qualified_name = name or _qualified_name(callable)

            if inherit:
                transaction.path = qualified_name

            trace = transaction.function_trace(qualified_name)
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator

def external_trace(index):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            try:
                transaction = _context.transactions[-1]
            except IndexError:
                return callable(*args, **kwargs)

            trace = transaction.external_trace(args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator

def memcache_trace(index):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            try:
                transaction = _context.transactions[-1]
            except IndexError:
                return callable(*args, **kwargs)

            trace = transaction.memcache_trace(args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator

def database_trace(index):

    def decorator(callable):

        def wrapper(*args, **kwargs):
            try:
                transaction = _context.transactions[-1]
            except IndexError:
                return callable(*args, **kwargs)

            trace = transaction.database_trace(args[index])
            trace.__enter__()

            try:
                return callable(*args, **kwargs)
            finally:
                trace.__exit__(None, None, None)

        return wrapper

    return decorator
