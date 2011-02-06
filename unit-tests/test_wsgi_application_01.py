import unittest

import newrelic

settings = newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = newrelic.LOG_VERBOSEDEBUG

_application = newrelic.application("UnitTests")

def _wsgiapp_function(self, *args):
    transaction = newrelic.transaction()
    assert transaction != None
_wsgiapp_function = newrelic.WSGIApplication(_application, _wsgiapp_function)

class _wsgiapp_class:
    def __init__(self, *args):
        pass
    def __call__(self):
        transaction = newrelic.transaction()
        assert transaction != None
_wsgiapp_class = newrelic.WSGIApplication(_application, _wsgiapp_class)

@newrelic.wsgi_application("UnitTests")
def _wsgiapp_function_decorator(self, *args):
    transaction = newrelic.transaction()
    assert transaction != None

@newrelic.wsgi_application("UnitTests")
class _wsgiapp_class_decorator:
    def __init__(self, *args):
        pass
    def __call__(self):
        transaction = newrelic.transaction()
        assert transaction != None

class WSGIApplicationTests01(unittest.TestCase):

    def setUp(self):
        newrelic.log(newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        newrelic.log(newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_wsgiapp_function(self):
        environ = { "REQUEST_URI": "/wsgiapp_function" }
        _wsgiapp_function(environ, None)

    def _wsgiapp_method(self, *args):
        transaction = newrelic.transaction()
        self.assertNotEqual(transaction, None)
    _wsgiapp_method = newrelic.WSGIApplication(_application, _wsgiapp_method)

    def test_wsgiapp_method(self):
        environ = { "REQUEST_URI": "/wsgiapp_method" }
        self._wsgiapp_method(environ, None)

    def test_wsgiapp_class(self):
        environ = { "REQUEST_URI": "/wsgiapp_class" }
        _wsgiapp_class(environ, None)

    def test_wsgiapp_function_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_function_decorator" }
        _wsgiapp_function_decorator(environ, None)

    @newrelic.wsgi_application("UnitTests")
    def _wsgiapp_method_decorator(self, *args):
        transaction = newrelic.transaction()
        self.assertNotEqual(transaction, None)

    def test_wsgiapp_method_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_method_decorator" }
        self._wsgiapp_method_decorator(environ, None)

    def test_wsgiapp_class_decorator(self):
        environ = { "REQUEST_URI": "/wsgiapp_class_decorator" }
        _wsgiapp_class_decorator(environ, None)

if __name__ == '__main__':
    unittest.main()
