from __future__ import with_statement
import unittest

import newrelic.api.settings
import newrelic.api.application
from newrelic.api.web_transaction import WebTransaction, WSGIApplicationWrapper

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

class TestCrossProcess(unittest.TestCase):
    """
    Test the cross tier feature.
    """

    def test_no_incoming_cross_pid(self):
        # Make request without HTTP_X_NEWRELIC_ID.
        # Make sure X-NewRelic-App-Data is absent in response.
        pass

    def test_cross_pid(self):
        # Make request with HTTP_X_NEWRELIC_ID.
        # Make sure X-NewRelic-App-Data is present in response.
        # Make sure the metric was created.
        pass

    def test_blank_incoming_cross_pid(self):
        # Make request with HTTP_X_NEWRELIC_ID but leave the value blank.
        # Check to make sure response header is still present.
        # Check to make sure the metric wasn't added.
        pass

class TestResponseHeaderJSON(unittest.TestCase):
    """Tests the build_cross_process_header() function."""

    def test_response_header_content_with_content_length(self):
        # Unpack the X-NewRelic-App-Data and check the contents of json.

        environ = {"CONTENT_LENGTH":"5", "REQUEST_URI": "/web_transaction" }

        expected_header = u'["305249#35857", "WebTransaction/Uri%s"'\
                ', 0.000000, 0.010000, 5]' % environ.get('REQUEST_URI')
        response_time = 0.01

        transaction = WebTransaction(application, environ)
        transaction._settings = newrelic.core.config.create_settings_snapshot(
                {"cross_process_id":"305249#35857"})
        transaction.enabled = True
        with transaction:
            header = WSGIApplicationWrapper.build_cross_process_header(
                    transaction, environ, response_time)
        self.assertEqual(header, expected_header)

    def test_response_header_content_without_content_length(self):
        # Unpack the X-NewRelic-App-Data and check the contents of json.

        environ = { "REQUEST_URI": "/web_transaction" }

        expected_header = u'["305249#35857", "WebTransaction/Uri%s"'\
                ', 0.000000, 0.010000, -1]' % environ.get('REQUEST_URI')
        response_time = 0.01

        transaction = WebTransaction(application, environ)
        transaction._settings = newrelic.core.config.create_settings_snapshot(
                {"cross_process_id":"305249#35857"})
        transaction.enabled = True
        with transaction:
            header = WSGIApplicationWrapper.build_cross_process_header(
                    transaction, environ, response_time)
        self.assertEqual(header, expected_header)


if __name__ == '__main__':
    unittest.main()
