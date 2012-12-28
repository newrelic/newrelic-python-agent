import unittest
import newrelic.api.settings
import newrelic.api.application
#import newrelic.tests.test_cases

import newrelic.agent

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

class TestCrossProcess(unittest.TestCase):
    """
    Test the cross tier feature.
    """

    def setUp(self):
        settings.cross_process_id = "305249#35857"

    def test_no_incoming_cross_pid(self):
        # Make request without HTTP_X_NEWRELIC_ID.
        # Make sure X-NewRelic-App-Data is absent in response.
        settings.cross_process.enabled = True
        print "Running QXY"

    def test_cross_pid(self):
        # Make request with HTTP_X_NEWRELIC_ID.
        # Make sure X-NewRelic-App-Data is present in response.
        # Make sure the metric was created.
        pass

    def test_response_header_content(self):
        # Unpack the X-NewRelic-App-Data and check the contents of json.
        environ = { "HTTP_X_NEWRELIC_ID": "VwYCU1JaGwAFXFRW",
                "CONTENT_LENGTH":"5"}
        transaction = newrelic.api.web_transaction.WebTransaction(application,
                environ)
        with transaction:
            print newrelic.api.web_transaction.build_nr_response_header(transaction, environ)
            

    def test_blank_incoming_cross_pid(self):
        # Make request with HTTP_X_NEWRELIC_ID but leave the value blank.
        # Check to make sure response header is still present.
        # Check to make sure the metric wasn't added.
        pass


if __name__ == '__main__':
    unittest.main()
