import logging
import unittest

import newrelic.tests.test_cases

import newrelic.packages.six as six

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.web_transaction

settings = newrelic.api.settings.settings()
_application = newrelic.api.application.application_instance()

def _wsgiapp_function(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None
    input = environ.get('wsgi.input')
    try:
        if input and hasattr(input, 'read'):
            input.read()
        if input and hasattr(input, 'readline'):
            input.readline()
        if input and hasattr(input, 'readlines'):
            input.readlines()
    except Exception:
        pass
_wsgiapp_function = newrelic.api.web_transaction.WSGIApplicationWrapper(
        _wsgiapp_function, _application)

def _wsgiapp_function_error(environ, start_response):
    raise RuntimeError("_wsgiapp_function_error")
_wsgiapp_function_error = newrelic.api.web_transaction.WSGIApplicationWrapper(
        _wsgiapp_function_error, _application)

class _wsgiapp_class:
    def __init__(self, environ, start_response):
        pass
    def __call__(self):
        transaction = newrelic.api.transaction.current_transaction()
        assert transaction != None
_wsgiapp_class = newrelic.api.web_transaction.WSGIApplicationWrapper(
        _wsgiapp_class, _application)

@newrelic.api.web_transaction.wsgi_application(_application.name)
def _wsgiapp_function_decorator(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application()
def _wsgiapp_function_decorator_default(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application(
        name='wsgiapp_named_wsgi_application', group='Group')
def _wsgiapp_named_wsgi_application(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application(
        name='wsgiapp_named_wsgi_application_inner', group='Group')
def _wsgiapp_named_wsgi_application_inner(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application(
        name='wsgiapp_named_wsgi_application_outer', group='Group')
def _wsgiapp_named_wsgi_application_outer(environ, start_response):
    return _wsgiapp_named_wsgi_application_inner(
            environ, start_response)

@newrelic.api.web_transaction.wsgi_application(framework='Framework')
def _wsgiapp_named_framework_wsgi_application(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application(framework=('Framework', '1'))
def _wsgiapp_named_framework_wsgi_application_version(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application(framework=('Framework', '1'))
def _wsgiapp_named_framework_wsgi_application_inner(environ, start_response):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application(framework=('Framework', '2'))
def _wsgiapp_named_framework_wsgi_application_outer(environ, start_response):
    return _wsgiapp_named_framework_wsgi_application_inner(
            environ, start_response)

# Python 2.5 doesn't have class decorators.
#@newrelic.api.web_transaction.wsgi_application(_application.name)
class _wsgiapp_class_decorator:
    def __init__(self, environ, start_response):
        pass
    def __call__(self):
        transaction = newrelic.api.web_transaction.current_transaction()
        assert transaction != None
_wsgiapp_class_decorator = newrelic.api.web_transaction.wsgi_application(_application.name)(_wsgiapp_class_decorator)

class Generator2:
    def __init__(self, iterable, callback, environ):
        self.__iterable = iterable
        self.__callback = callback
        self.__environ = environ
    def __iter__(self):
        for item in self.__iterable:
            yield item
    def close(self):
        try:
            if hasattr(self.__iterable, 'close'):
                self.__iterable.close()
        finally:
            self.__callback(self.__environ)

class ExecuteOnCompletion2:
    def __init__(self, application, callback):
        self.__application = application
        self.__callback = callback
    def __call__(self, environ, start_response):
        try:
            result = self.__application(environ, start_response)
        except:
            self.__callback(environ)
            raise
        return Generator2(result, self.__callback, environ)

@newrelic.api.web_transaction.wsgi_application()
def _wsgi_app_yield_exception(environ, start_response):
    def application(environ, start_response):
        start_response('200 OK', [])
        yield "1\n"
        yield "2\n"
        raise RuntimeError('error between yields')
        yield "3\n"
        yield "4\n"
        yield "5\n"

    def callback(environ):
        raise NotImplementedError('error in close')

    _application = ExecuteOnCompletion2(application, callback)
    return _application(environ, start_response)

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_wsgiapp_function(self):
        environ = { "REQUEST_URI": "/wsgiapp_function" }
        _wsgiapp_function(environ, None).close()

    def test_wsgiapp_function_error(self):
        environ = { "REQUEST_URI": "/wsgiapp_function_error" }
        try:
            _wsgiapp_function_error(environ, None)
        except RuntimeError:
            pass

    def _wsgiapp_method(self, *args):
        transaction = newrelic.api.transaction.current_transaction()
        self.assertNotEqual(transaction, None)
    _wsgiapp_method = newrelic.api.web_transaction.WSGIApplicationWrapper(
            _wsgiapp_method, _application)

    def test_wsgiapp_method(self):
        environ = { "REQUEST_URI": "/wsgiapp_method" }
        self._wsgiapp_method(environ, None).close()

    def test_wsgiapp_class(self):
        environ = { "REQUEST_URI": "/wsgiapp_class" }
        _wsgiapp_class(environ, None).close()

    def test_wsgiapp_function_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_function_decorator" }
        _wsgiapp_function_decorator(environ, None).close()

    def test_wsgiapp_function_decorator_default(self):
        environ = { "REQUEST_URI": "/wsgiapp_function_decorator_default" }
        _wsgiapp_function_decorator_default(environ, None).close()

    def test_wsgiapp_named_wsgi_application(self):
        environ = { "REQUEST_URI": "/wsgiapp_named_wsgi_application" }
        _wsgiapp_named_wsgi_application(environ, None).close()

    def test_wsgiapp_named_wsgi_application_nested(self):
        environ = { "REQUEST_URI": "/wsgiapp_named_wsgi_application_nested" }
        _wsgiapp_named_wsgi_application_outer(environ, None).close()

    def test_wsgiapp_named_framework_wsgi_application(self):
        environ = { "REQUEST_URI":
                "/wsgiapp_named_framework_wsgi_application" }
        _wsgiapp_named_framework_wsgi_application(environ, None).close()

    def test_wsgiapp_named_framework_wsgi_application_version(self):
        environ = { "REQUEST_URI":
                "/wsgiapp_named_framework_wsgi_application_version" }
        _wsgiapp_named_framework_wsgi_application_version(environ, None).close()

    def test_wsgiapp_named_framework_wsgi_application_nested(self):
        environ = { "REQUEST_URI":
                "/wsgiapp_named_framework_wsgi_application_outer" }
        _wsgiapp_named_framework_wsgi_application_outer(environ, None).close()

    @newrelic.api.web_transaction.wsgi_application(_application.name)
    def _wsgiapp_method_decorator(self, *args):
        transaction = newrelic.api.transaction.current_transaction()
        self.assertNotEqual(transaction, None)

    def test_wsgiapp_method_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_method_decorator" }
        self._wsgiapp_method_decorator(environ, None).close()

    def test_wsgiapp_class_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_class_decorator" }
        _wsgiapp_class_decorator(environ, None).close()

    def test_wsgiapp_function_input(self):
        environ = { "REQUEST_URI": "/wsgiapp_function_input",
                    "wsgi.input": six.StringIO() }
        _wsgiapp_function(environ, None).close()

    def test_wsgiapp_function_read_exception(self):
        class Input(object):
            def read(self):
                raise RuntimeError('fail')
        environ = { "REQUEST_URI": "/wsgiapp_function_read_exception",
                    "wsgi.input": Input() }
        _wsgiapp_function(environ, None).close()

    def test_wsgiapp_function_readline_exception(self):
        class Input(object):
            def readline(self):
                raise RuntimeError('fail')
        environ = { "REQUEST_URI": "/wsgiapp_function_readline_exception",
                    "wsgi.input": Input() }
        _wsgiapp_function(environ, None).close()

    def test_wsgiapp_function_realines_exception(self):
        class Input(object):
            def readlines(self):
                raise RuntimeError('fail')
        environ = { "REQUEST_URI": "/wsgiapp_function_realines_exception",
                    "wsgi.input": Input() }
        _wsgiapp_function(environ, None).close()

    def test_wsgiapp_yield_exception(self):
        environ = { "REQUEST_URI": "/wsgiapp_yield_exception" }
        def start_response(*args): pass
        iterable = _wsgi_app_yield_exception(environ, start_response)
        try:
            try:
                for item in iterable:
                    pass
            finally:
                iterable.close()
        except Exception:
            pass

if __name__ == '__main__':
    unittest.main()
