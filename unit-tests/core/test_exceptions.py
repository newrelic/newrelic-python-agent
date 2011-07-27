'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.exceptions import ForceRestartException,\
    raise_newrelic_exception

class ExceptionTest(unittest.TestCase):
    def test_force_restart(self):
        try:
            raise raise_newrelic_exception("ForceRestartException", "restart")
        except ForceRestartException as ex:
            self.assertEqual("restart", str(ex))


class RestartExceptionTest(unittest.TestCase):
    def test_constructor(self):
        try:
            raise ForceRestartException("Test")
        except ForceRestartException:
            pass



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()