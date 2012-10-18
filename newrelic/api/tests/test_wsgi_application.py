import logging
import StringIO
import unittest

import newrelic.tests.test_cases

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
    except:
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

# Python 2.5 doesn't have class decorators.
#@newrelic.api.web_transaction.wsgi_application(_application.name)
class _wsgiapp_class_decorator:
    def __init__(self, environ, start_response):
        pass
    def __call__(self):
        transaction = newrelic.api.web_transaction.current_transaction()
        assert transaction != None
_wsgiapp_class_decorator = newrelic.api.web_transaction.wsgi_application(_application.name)(_wsgiapp_class_decorator)

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
                    "wsgi.input": StringIO.StringIO() }
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

if __name__ == '__main__':
    unittest.main()
