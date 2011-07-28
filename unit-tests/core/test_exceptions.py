'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.exceptions import ForceRestartException,ForceShutdownException,\
    raise_newrelic_exception

class ExceptionTest(unittest.TestCase):
    def test_force_restart(self):
        try:
            raise raise_newrelic_exception("ForceRestartException", "restart")
        except ForceRestartException as ex:
            self.assertEqual("restart", str(ex))
        try:
            raise raise_newrelic_exception("NewRelic::Agent::ForceRestartException", "restart")
        except ForceRestartException as ex:
            self.assertEqual("restart", str(ex))
            
            
    def test_force_shutdown(self):
        try:
            raise raise_newrelic_exception("ForceShutdownException", "shutdown")
        except ForceShutdownException as ex:
            self.assertEqual("shutdown", str(ex))


class RestartExceptionTest(unittest.TestCase):
    def test_constructor(self):
        try:
            raise ForceRestartException("Test")
        except ForceRestartException:
            pass



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()