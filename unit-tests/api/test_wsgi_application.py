import unittest

import newrelic.api.settings
import newrelic.api.log_file
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.web_transaction

settings = newrelic.api.settings.settings()
settings.app_name = "UnitTests"
settings.log_file = "%s.log" % __file__
settings.log_level = newrelic.api.log_file.LOG_VERBOSEDEBUG
settings.transaction_tracer.transaction_threshold = 0

_application = newrelic.api.application.application_instance("UnitTests")

def _wsgiapp_function(self, *args):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None
_wsgiapp_function = newrelic.api.web_transaction.WSGIApplicationWrapper(
        _wsgiapp_function, _application)

def _wsgiapp_function_error(self, *args):
    raise RuntimeError("_wsgiapp_function_error")
_wsgiapp_function_error = newrelic.api.web_transaction.WSGIApplicationWrapper(
        _wsgiapp_function_error, _application)

class _wsgiapp_class:
    def __init__(self, *args):
        pass
    def __call__(self):
        transaction = newrelic.api.transaction.current_transaction()
        assert transaction != None
_wsgiapp_class = newrelic.api.web_transaction.WSGIApplicationWrapper(
        _wsgiapp_class, _application)

@newrelic.api.web_transaction.wsgi_application("UnitTests")
def _wsgiapp_function_decorator(self, *args):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application()
def _wsgiapp_function_decorator_default(self, *args):
    transaction = newrelic.api.transaction.current_transaction()
    assert transaction != None

@newrelic.api.web_transaction.wsgi_application("UnitTests")
class _wsgiapp_class_decorator:
    def __init__(self, *args):
        pass
    def __call__(self):
        transaction = newrelic.api.web_transaction.current_transaction()
        assert transaction != None

class WSGIApplicationTests(unittest.TestCase):

    def setUp(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STARTING - %s" % self._testMethodName)

    def tearDown(self):
        newrelic.api.log_file.log(newrelic.api.log_file.LOG_DEBUG,
                "STOPPING - %s" % self._testMethodName)

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

    @newrelic.api.web_transaction.wsgi_application("UnitTests")
    def _wsgiapp_method_decorator(self, *args):
        transaction = newrelic.api.transaction.current_transaction()
        self.assertNotEqual(transaction, None)

    def test_wsgiapp_method_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_method_decorator" }
        self._wsgiapp_method_decorator(environ, None).close()

    def test_wsgiapp_class_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_class_decorator" }
        _wsgiapp_class_decorator(environ, None).close()

if __name__ == '__main__':
    unittest.main()
