import unittest
import time
import sys

import _newrelic

settings = _newrelic.settings()
settings.log_file = "%s.log" % __file__
settings.log_level = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

#@_newrelic.function_trace(name='_test_function_1')
def _test_function_1():
    time.sleep(1.0)
_test_function_1 = _newrelic.function_trace(
        name='_test_function_1')(_test_function_1)

#@_newrelic.function_trace()
def _test_function_nn_1():
    time.sleep(0.1)
_test_function_nn_1 = _newrelic.function_trace()(_test_function_nn_1)

class _test_class_nn_2:
    def _test_function(self):
        time.sleep(0.1)

_test_class_instance_nn_2 = _test_class_nn_2()
_test_class_instance_nn_2._test_function = _newrelic.function_trace()(
        _test_class_instance_nn_2._test_function)

class _test_class_nn_3(object):
    def _test_function(self):
        time.sleep(0.1)

_test_class_instance_nn_3 = _test_class_nn_3()
_test_class_instance_nn_3._test_function = _newrelic.function_trace()(
        _test_class_instance_nn_3._test_function)

class _test_class_nn_4:
    #@_newrelic.function_trace()
    def _test_function(self):
        time.sleep(0.1)
    _test_function = _newrelic.function_trace()(_test_function)

_test_class_instance_nn_4 = _test_class_nn_4()

class _test_class_nn_5(object):
    #@_newrelic.function_trace()
    def _test_function(self):
        time.sleep(0.1)
    _test_function = _newrelic.function_trace()(_test_function)

_test_class_instance_nn_5 = _test_class_nn_5()

def _test_function_6(name):
    time.sleep(0.1)
_test_function_6 = _newrelic.function_trace(lambda x: x)(_test_function_6)

class FunctionTraceTests(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_function_trace(self):
        environ = { "REQUEST_URI": "/function_trace" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.2)
            with _newrelic.FunctionTrace(transaction, "function-1"):
                time.sleep(0.1)
                with _newrelic.FunctionTrace(transaction, "function-1-1"):
                    time.sleep(0.1)
                with _newrelic.FunctionTrace(transaction, "function-1-2"):
                    time.sleep(0.1)
                time.sleep(0.1)
            with _newrelic.FunctionTrace(transaction, "function-2"):
                time.sleep(0.1)
                with _newrelic.FunctionTrace(transaction, "function-2-1"):
                    time.sleep(0.1)
                    with _newrelic.FunctionTrace(transaction, "function-2-1-1"):
                        time.sleep(0.1)
                    time.sleep(0.1)
                time.sleep(0.1)
            time.sleep(0.2)

    def test_transaction_not_running(self):
        environ = { "REQUEST_URI": "/transaction_not_running" }
        transaction = _newrelic.WebTransaction(application, environ)
        try:
            with _newrelic.FunctionTrace(transaction, "function"):
                time.sleep(0.1)
        except RuntimeError:
            pass

    def test_function_trace_decorator(self):
        environ = { "REQUEST_URI": "/function_trace_decorator" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_1()
            time.sleep(0.1)

    def test_function_trace_decorator_error(self):
        environ = { "REQUEST_URI": "/function_trace_decorator_error" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            try:
                _test_function_1()
            except TypeError:
                pass

    def test_function_trace_decorator_no_name(self):
        environ = { "REQUEST_URI": "/function_trace_decorator_no_name" }
        transaction = _newrelic.WebTransaction(application, environ)
        with transaction:
            time.sleep(0.1)
            _test_function_nn_1()
            _test_class_instance_nn_2._test_function()
            _test_class_instance_nn_3._test_function()
            _test_class_instance_nn_4._test_function()
            _test_class_instance_nn_5._test_function()
            _test_function_6("function+lambda")
            time.sleep(0.1)

if __name__ == '__main__':
    unittest.main()
