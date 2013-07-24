import unittest
import time

import newrelic.packages.six as six

from newrelic.api.application import application_instance
from newrelic.core.config import global_settings, create_settings_snapshot
from newrelic.api.web_transaction import WebTransaction, wsgi_application
from newrelic.api.transaction import current_transaction
from newrelic.api.object_wrapper import callable_name

class MockApplication(object):
    def __init__(self, settings, name='Python Application'):
        self.global_settings = create_settings_snapshot()
        self.global_settings.enabled = True
        self.settings = create_settings_snapshot(settings)
        self.name = name
        self.active = True
        self.enabled = True
        self.thread_utilization = None
    def activate(self):
        pass
    def normalize_name(self, name, rule_type):
        return name, False
    def record_transaction(self, data, *args):
        return None

class TestCase(unittest.TestCase):

    def test_default(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = None

        application = MockApplication(settings)

        # Should be named after the raw REQUEST_URI.

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Uri/url'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_default_name(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = None

        application = MockApplication(settings)

        # Should be named after the specific name and group.

        @wsgi_application(application=application, name='Name', group='Group')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Group/Name'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_default_framework(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = None

        application = MockApplication(settings)

        # Should be named after first WSGI component which was wrapped.

        @wsgi_application(application=application, framework='Framework')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            self.assertTrue(('Framework', None) in transaction._frameworks,
                    'The saved list of frameworks is %r.' % (
                    transaction._frameworks))

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_default_framework_nested_1(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = None

        application = MockApplication(settings)

        # Should be named after the last WSGI component which was wrapped
        # and tagged as being for a framework.

        @wsgi_application(application=application,
                framework=('Framework-2', '1.0'))
        def test_application_2(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_2)

            self.assertTrue(('Framework-2', '1.0') in transaction._frameworks,
                    'The saved list of frameworks is %r.' % (
                    transaction._frameworks))

        path_2 = u'WebTransaction/Function/%s' % callable_name(
                test_application_2)

        @wsgi_application(application=application, framework='Framework-1')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            self.assertTrue(('Framework-1', None) in transaction._frameworks,
                    'The saved list of frameworks is %r.' % (
                    transaction._frameworks))

            return test_application_2(environ, start_response)

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_default_framework_nested_2(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = None

        application = MockApplication(settings)

        # Should be named after the last WSGI component which was wrapped
        # and tagged as being for a framework.

        @wsgi_application(application=application,
                framework=('Framework-2', '1.0'))
        def test_application_2(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_2)

            self.assertTrue(('Framework-2', '1.0') in transaction._frameworks,
                    'The saved list of frameworks is %r.' % (
                    transaction._frameworks))

        path_2 = u'WebTransaction/Function/%s' % callable_name(
                test_application_2)

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            return test_application_2(environ, start_response)

        path_1 = u'WebTransaction/Uri/url'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_uri(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'uri'

        application = MockApplication(settings)

        # Should be named after the raw REQUEST_URI.

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Uri/url'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_uri_name(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'uri'

        application = MockApplication(settings)

        # Should be named after the specific name and group.

        @wsgi_application(application=application, name='Name', group='Group')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Group/Name'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_uri_name_nested(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'uri'

        application = MockApplication(settings)

        # Should be named after the innermost specific name and group.

        @wsgi_application(application=application, name='Name-2', group='Group')
        def test_application_2(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_2)

        path_2 = u'WebTransaction/Group/Name-2'

        @wsgi_application(application=application, name='Name-1', group='Group')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            return test_application_2(environ, start_response)

        path_1 = u'WebTransaction/Group/Name-1'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_uri_name(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'uri'

        application = MockApplication(settings)

        # Should be named after the specific name and group.

        @wsgi_application(application=application, name='Name', group='Group')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Group/Name'

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_component(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'component'

        application = MockApplication(settings)

        # Should be named after first WSGI component which was wrapped.

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_component_nested(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'component'

        application = MockApplication(settings)

        # When nested, is still the first WSGI component which was wrapped
        # which was encountered.

        @wsgi_application(application=application)
        def test_application_2(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            return test_application_2(environ, start_response)

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_component_framework_nested(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'component'

        application = MockApplication(settings)

        # Even when nested is a framework, is still the first WSGI
        # component which was wrapped which was encountered.

        @wsgi_application(application=application, framework='Framework')
        def test_application_2(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            return test_application_2(environ, start_response)

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_framework(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'framework'

        application = MockApplication(settings)

        # Even when nested is a framework, is still the first WSGI
        # component which was wrapped which was encountered.

        @wsgi_application(application=application, framework='Framework')
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

    def test_framework_nested(self):
        settings = {}
        settings['transaction_name.naming_scheme'] = 'framework'

        application = MockApplication(settings)

        # Even when nested is a framework, is still the first WSGI
        # component which was wrapped which was encountered.

        @wsgi_application(application=application, framework='Framework')
        def test_application_2(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_2)

        path_2 = u'WebTransaction/Function/%s' % callable_name(
                test_application_2)

        @wsgi_application(application=application)
        def test_application_1(environ, start_response):
            transaction = current_transaction()

            self.assertNotEqual(transaction, None)
            self.assertTrue(transaction.enabled)

            self.assertEqual(transaction.path, path_1)

            return test_application_2(environ, start_response)

        path_1 = u'WebTransaction/Function/%s' % callable_name(
                test_application_1)

        environ = {}
        environ['REQUEST_URI'] = '/url'

        test_application_1(environ, None).close()

if __name__ == '__main__':
    unittest.main()
