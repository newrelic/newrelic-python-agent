'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest
from newrelic.core.agent import Agent, newrelic_agent


class AgentTest(unittest.TestCase):


    def test_instance(self):
        a = newrelic_agent()
        self.assertNotEqual(None, a)
        b = newrelic_agent()
        self.assertEqual(a,b)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()