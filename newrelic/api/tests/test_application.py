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

    def test_attribute_filter_before_registration(self):
        self.assertEqual(settings.attribute_filter, None)

    def test_attribute_filter_after_registration(self):
        application = newrelic.api.application.application_instance()
        attribute_filter = application.settings.attribute_filter

        # Performing an 'isinstance' test would require importing
        # newrelic.core.attribute_filter. Instead, let's just test
        # if attribute_filter has the right interface. (If it walks
        # like a duck, quacks like a duck...)

        self.assertTrue(hasattr(attribute_filter, 'apply'))
        self.assertTrue(hasattr(attribute_filter, 'rules'))
        self.assertTrue(hasattr(attribute_filter, 'enabled_destinations'))

if __name__ == '__main__':
    unittest.main()
