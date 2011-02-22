import unittest
import time
import sys
import sqlite3

import _newrelic

settings = _newrelic.settings()
settings.logfile = "%s.log" % __file__
settings.loglevel = _newrelic.LOG_VERBOSEDEBUG

application = _newrelic.application("UnitTests")

def _pre_function(*args, **kwargs):
    return args, kwargs

def _test_function(*args, **kwargs):
    return args, kwargs

class _test_class_1:
    def _test_function(self, *args, **kwargs):
        return args, kwargs

class _test_class_2(object):
    def _test_function(self, *args, **kwargs):
        return args, kwargs

class PreFunctionTests01(unittest.TestCase):

    def setUp(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STARTING - %s" %
                      self._testMethodName)

    def tearDown(self):
        _newrelic.log(_newrelic.LOG_DEBUG, "STOPPING - %s" %
                      self._testMethodName)

    def test_wrap_pre_function_1(self):
        o1 = _test_function
        o2 = _newrelic.wrap_pre_function(__name__, None, '_test_function',
                                         _pre_function)
        self.assertEqual(o1, o2)

    def test_wrap_pre_function_2(self):
        o1 = _test_class_1._test_function
        o2 = _newrelic.wrap_pre_function(__name__, '_test_class_1',
                                         '_test_function', _pre_function)
        self.assertEqual(o1, o2)

    def test_wrap_pre_function_3(self):
        o1 = _test_class_2._test_function
        o2 = _newrelic.wrap_pre_function(__name__, '_test_class_2',
                                         '_test_function', _pre_function)
        self.assertEqual(o1, o2)

    def test_wrap_pre_function_4(self):
        o1 = sqlite3.Cursor.execute
        o2 = _newrelic.wrap_pre_function('sqlite3', 'Cursor', 'execute',
                                         _pre_function)
        self.assertEqual(o1, o2)

if __name__ == '__main__':
    unittest.main()
