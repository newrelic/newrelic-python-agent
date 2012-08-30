from __future__ import with_statement
  
import logging
import unittest

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application

settings = newrelic.api.settings.settings()

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_create(self):
        application = newrelic.api.application.application_instance()
        self.assertEqual(application.name, settings.app_name)

    def test_enabled(self):
        application = newrelic.api.application.application_instance()
        self.assertTrue(application.enabled)
        application.enabled = False
        self.assertFalse(application.enabled)
        application.enabled = True
        self.assertTrue(application.enabled)

    def test_singleton(self):
        application1 = newrelic.api.application.application_instance()
        application2 = newrelic.api.application.application_instance()
        self.assertEqual(id(application1), id(application2))

if __name__ == '__main__':
    unittest.main()
