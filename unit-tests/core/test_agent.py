'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest

from newrelic.core.agent import Agent, newrelic_agent

import newrelic.core.config

_settings = newrelic.core.config.settings()

_settings.host = 'staging-collector.newrelic.com'
_settings.port = 80
_settings.license_key = 'd67afc830dab717fd163bfcb0b8b88423e9a1a3b'
_settings.app_name = 'Python Unit Test1'

class AgentTest(unittest.TestCase):


    def test_instance(self):
        a = newrelic_agent()
        self.assertNotEqual(None, a)
        b = newrelic_agent()
        self.assertEqual(a,b)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
