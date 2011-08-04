'''
Created on Jul 27, 2011

@author: sdaubin
'''
import unittest
import time

import newrelic.core.agent
import newrelic.core.config

_settings = newrelic.core.config.global_settings()

_settings.host = 'staging-collector.newrelic.com'
_settings.port = 80
_settings.license_key = 'd67afc830dab717fd163bfcb0b8b88423e9a1a3b'
_settings.app_name = 'Python Unit Test1'

class AgentTest(unittest.TestCase):

    def test_agent_singleton(self):
        a = newrelic.core.agent.agent()
        self.assertNotEqual(None, a)
        b = newrelic.core.agent.agent()
        self.assertEqual(a,b)

    def test_agent_connection(self):
        agent = newrelic.core.agent.agent()

        # FIXME This can be the only test which activates
        # the application as checks that not active first.

        name = _settings.app_name
        application_settings = agent.settings(name)
        self.assertEqual(application_settings, None)
        agent.activate(name)
        for i in range(10):
            application_settings = agent.settings(name)
            if application_settings:
                break
            time.sleep(0.5)
        self.assertNotEqual(application_settings, None)
        print application_settings
        agent.stop()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
