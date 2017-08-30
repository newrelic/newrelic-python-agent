import unittest

import newrelic.api.application
import newrelic.api.settings
import newrelic.tests.test_cases

from collections import namedtuple

from newrelic.api.transaction import Transaction
from newrelic.api.external_trace import ExternalTrace
from newrelic.common.encoding_utils import (obfuscate, json_encode)


settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()


class TestCatInterface(newrelic.tests.test_cases.TestCase):
    TransactionData = namedtuple('TransactionData',
            ['encoded_response_headers', 'response_encoded_data',
            'request_metadata'])

    def prepare_transaction(self, txn):
        txn.client_cross_process_id = "Meow"
        txn.start_time = 100
        txn.end_time = 200
        txn.guid = '02c574ebb384313d'
        txn._settings = settings
        txn._settings.cross_process_id = "1"
        txn._settings.encoding_key = "shhh"
        txn._settings.cross_application_tracer.enabled = True
        app_data = json_encode([txn._settings.cross_process_id,
                "WebTransaction/Uri/<undefined>", 0, 100, None, txn.guid,
                False])

        return TestCatInterface.TransactionData(
                # encoded_response_headers
                [('X-NewRelic-App-Data', obfuscate(app_data,
                txn._settings.encoding_key))],

                # response_encoded_data
                'eyJYLU5ld1JlbGljLUlEIjoiUWc9PSIsIlgtTmV3UmVsaWMtVHJhbnNhY' +
                '3Rpb24iOiJLRXBZV2hCZFgxd1dDZ3BiUzF4YldVQU1Ta1FWQ1FRYkZrUk' +
                'tXRUVMWFY5SERRb0tRRkJjVzBKYkRFcGZTbDFjUUZGZERVZFpTalU9In0=',

                # request_metadata
                'eyJYLU5ld1JlbGljLUFwcC1EYXRhIjoiS0VwWlNsOUtQdzBSUEJvSkhSc' +
                '0pDd2NCQndaY1BSb0JYRlFkQmhjTkRnRWREUXhXVVVSWVJFSllXRVFkSF' +
                'FRRVgwcFlXaEJkWDF3V0NncGJTMXhiV1VBTVNrUVZDUVFiRmpVPSJ9')

    def test_generate_response_headers(self):
        # Test without headers
        with Transaction(application) as txn:
            self.assertEqual(txn._generate_response_headers(), [])

        # Test with headers
        with Transaction(application) as txn:
            data = self.prepare_transaction(txn)
            self.assertEqual(
                    txn._generate_response_headers(),
                    data.encoded_response_headers)

    def test_get_response_metadata(self):
        # Test without headers.
        with Transaction(application) as txn:
            self.assertIsNone(txn.get_response_metadata())

        # Test with headers.
        with Transaction(application) as txn:
            data = self.prepare_transaction(txn)
            self.assertEqual(txn.get_response_metadata(),
                    data.request_metadata)

    def test_process_request_metadata(self):
        # Test faulty data (does not raise).
        with Transaction(application) as txn:
            self.assertIsNone(txn.process_request_metadata('meow'))

        # Test good data.
        with Transaction(application) as txn:
            data = self.prepare_transaction(txn)
            self.assertIsNone(txn.process_request_metadata(
                    data.request_metadata))

    def test_generate_request_headers(self):
        library = ""
        url = "cat/meow"
        with Transaction(application) as txn:
            self.prepare_transaction(txn)
            trace = ExternalTrace(txn, library, url)
            resp_dict = dict(trace.generate_request_headers(txn))
            # TODO: check values-- requires better understanding of path hash.
            self.assertTrue('X-NewRelic-ID' in resp_dict)
            self.assertTrue('X-NewRelic-Transaction' in resp_dict)

    def test_get_request_metadata(self):
        library = ""
        url = "cat/meow"
        with Transaction(application) as txn:
            data = self.prepare_transaction(txn)
            trace = ExternalTrace(txn, library, url)
            self.assertEqual(trace.get_request_metadata(txn),
                    data.response_encoded_data)

    def test_process_response_metadata(self):
        library = ""
        url = "cat/meow"
        with Transaction(application) as txn:
            data = self.prepare_transaction(txn)
            trace = ExternalTrace(txn, library, url)

            self.assertIsNone(trace.process_response_metadata(
                    data.response_encoded_data))


if __name__ == '__main__':
    unittest.main()
