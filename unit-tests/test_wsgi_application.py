import unittest

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

_application = _newrelic.application("UnitTests")

def _wsgiapp_function(self, *args):
    transaction = _newrelic.transaction()
    assert transaction != None
_wsgiapp_function = _newrelic.WebTransactionWrapper(
        _wsgiapp_function, _application)

def _wsgiapp_function_error(self, *args):
    raise RuntimeError("_wsgiapp_function_error")
_wsgiapp_function_error = _newrelic.WebTransactionWrapper(
        _wsgiapp_function_error, _application)

class _wsgiapp_class:
    def __init__(self, *args):
        pass
    def __call__(self):
        transaction = _newrelic.transaction()
        assert transaction != None
_wsgiapp_class = _newrelic.WebTransactionWrapper(
        _wsgiapp_class, _application)

@_newrelic.web_transaction("UnitTests")
def _wsgiapp_function_decorator(self, *args):
    transaction = _newrelic.transaction()
    assert transaction != None

@_newrelic.web_transaction("UnitTests")
class _wsgiapp_class_decorator:
    def __init__(self, *args):
        pass
    def __call__(self):
        transaction = _newrelic.transaction()
        assert transaction != None

class WSGIApplicationTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

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
        transaction = _newrelic.transaction()
        self.assertNotEqual(transaction, None)
    _wsgiapp_method = _newrelic.WebTransactionWrapper(
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

    @_newrelic.web_transaction("UnitTests")
    def _wsgiapp_method_decorator(self, *args):
        transaction = _newrelic.transaction()
        self.assertNotEqual(transaction, None)

    def test_wsgiapp_method_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_method_decorator" }
        self._wsgiapp_method_decorator(environ, None).close()

    def test_wsgiapp_class_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_class_decorator" }
        _wsgiapp_class_decorator(environ, None).close()

if __name__ == '__main__':
    unittest.main()
