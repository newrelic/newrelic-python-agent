# vim: set fileencoding=utf-8 :

import logging
import unittest
import math

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

class TestCase(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_int(self):
        for i in range(100):
            application.record_custom_metric("CustomMetricTests01/Int", i)

    def test_float(self):
        for i in map(math.sqrt, range(100)):
            application.record_custom_metric("CustomMetricTests01/Float", i)

    def test_unicode(self):
        for i in map(math.sqrt, range(100)):
            application.record_custom_metric(u"CustomMetricTests01/√√√√√", i)

    def test_disabled(self):
        # XXX This will actually always work as the record_custom_metric()
        # method doesn't check enabled flag. Is expected at this point
        # that any internal code using the method checks before making
        # the class.

        application.enabled = False
        application.record_custom_metric("CustomMetricTests01/Disabled", 1)
        application.enabled = True

if __name__ == '__main__':
    unittest.main()
