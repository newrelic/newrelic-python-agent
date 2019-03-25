import copy
import unittest

import newrelic.api.application
import newrelic.api.settings
import newrelic.tests.test_cases

from collections import namedtuple

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import Transaction
from newrelic.common.encoding_utils import deobfuscate, json_decode


TransactionData = namedtuple('TransactionData', ['obfuscated_request_headers',
        'obfuscated_response_headers', 'outgoing_encoded_data',
        'incoming_response_encoded_data'])


txn_cat_info = TransactionData(
        # obfuscated_request_headers
        # Values are JSON encoded, and then obfuscated.
        [('X-NewRelic-ID', 'QktZ'), ('X-NewRelic-Transaction', ('KEpYWhBdX1wW'
        'CgpbS1xbWUAMSkQVCQQbFkRKWEELXV9HDQoKQFBcW0JbDEpfSg0LEAlfWERcSjU=')),
        ('X-NewRelic-Synthetics', 'Wruff')],

        # obfuscated_response_headers
        # Value is JSON encoded list describing event, that is then obfuscated.
        [('X-NewRelic-App-Data', 'KEpZS0JKREokDQo8AQkGGxILHAEcBkc9AQFHVAYGDA0V'
        'AQYNF1ZKRENEWVhDREVZX0pYWhBdX1wWCgpbS1xbWUAMSkQVCQQbFjU=')],

        # outgoing_encoded_data
        # Data is a list of tuples (header, value) that inclues
        # 'X-NewRelic-ID', 'X-NewRelic-Transaction', and
        # 'X-NewRelic-Synthetics'. Values are obfuscated, and all orders of
        # pairs are represented. The full payload is cast to a dictionary,
        # JSON encoded, and finally base64 encoded.
        [('eyJYLU5ld1JlbGljLUlEIjoiUWt0WiIsIlgtTmV3UmVsaWMtVHJhbnNhY3Rpb24iOi'
        'JLRXBZV2hCZFgxd1dDZ3BiUzF4YldVQU1Ta1FWQ1FRYkZrUktXRUVMWFY5SERRb0tRRk'
        'JjVzBKYkRFcGZTZzBMRUFsZldFUmNTalU9IiwiWC1OZXdSZWxpYy1TeW50aGV0aWNzIj'
        'oiV3J1ZmYifQ=='), ('eyJYLU5ld1JlbGljLUlEIjoiUWt0WiIsIlgtTmV3UmVsaWMt'
        'U3ludGhldGljcyI6IldydWZmIiwiWC1OZXdSZWxpYy1UcmFuc2FjdGlvbiI6IktFcFlX'
        'aEJkWDF3V0NncGJTMXhiV1VBTVNrUVZDUVFiRmtSS1dFRUxYVjlIRFFvS1FGQmNXMEpi'
        'REVwZlNnMExFQWxmV0VSY1NqVT0ifQ=='), ('eyJYLU5ld1JlbGljLVRyYW5zYWN0aW'
        '9uIjoiS0VwWVdoQmRYMXdXQ2dwYlMxeGJXVUFNU2tRVkNRUWJGa1JLV0VFTFhWOUhEUW'
        '9LUUZCY1cwSmJERXBmU2cwTEVBbGZXRVJjU2pVPSIsIlgtTmV3UmVsaWMtSUQiOiJRa3'
        'RaIiwiWC1OZXdSZWxpYy1TeW50aGV0aWNzIjoiV3J1ZmYifQ=='), ('eyJYLU5ld1Jl'
        'bGljLVRyYW5zYWN0aW9uIjoiS0VwWVdoQmRYMXdXQ2dwYlMxeGJXVUFNU2tRVkNRUWJG'
        'a1JLV0VFTFhWOUhEUW9LUUZCY1cwSmJERXBmU2cwTEVBbGZXRVJjU2pVPSIsIlgtTmV3'
        'UmVsaWMtU3ludGhldGljcyI6IldydWZmIiwiWC1OZXdSZWxpYy1JRCI6IlFrdFoifQ='
        '='), ('eyJYLU5ld1JlbGljLVN5bnRoZXRpY3MiOiJXcnVmZiIsIlgtTmV3UmVsaWMtS'
        'UQiOiJRa3RaIiwiWC1OZXdSZWxpYy1UcmFuc2FjdGlvbiI6IktFcFlXaEJkWDF3V0Nnc'
        'GJTMXhiV1VBTVNrUVZDUVFiRmtSS1dFRUxYVjlIRFFvS1FGQmNXMEpiREVwZlNnMExFQ'
        'WxmV0VSY1NqVT0ifQ=='), ('eyJYLU5ld1JlbGljLVN5bnRoZXRpY3MiOiJXcnVmZiI'
        'sIlgtTmV3UmVsaWMtVHJhbnNhY3Rpb24iOiJLRXBZV2hCZFgxd1dDZ3BiUzF4YldVQU1'
        'Ta1FWQ1FRYkZrUktXRUVMWFY5SERRb0tRRkJjVzBKYkRFcGZTZzBMRUFsZldFUmNTalU'
        '9IiwiWC1OZXdSZWxpYy1JRCI6IlFrdFoifQ==')],

        # incoming_response_encoded_data
        # txn_cat_info is a list of tuples (header, value) that includes
        # 'X-NewRelic-App-Data'. Values are obfuscated. The full payload is
        # cast to a dictionary, JSON encoded, and finally base64 encoded.
        ('eyJYLU5ld1JlbGljLUFwcC1EYXRhIjoiS0VwWlMwSktSRW9rRFFvOEFRa0dHeElMSEFF'
         'Y0JrYzlBUUZIVkFZR0RBMFZBUVlORjFaS1JFTkVXVmhEUkVWWlgwcFlXaEJkWDF3V0Nn'
         'cGJTMXhiV1VBTVNrUVZDUVFiRmpVPSJ9'))


class TestCatInterface(newrelic.tests.test_cases.TestCase):
    requires_collector = True

    def setUp(self):
        super(TestCatInterface, self).setUp()
        self.app_api = newrelic.api.application.application_instance()
        self.agent_settings = copy.deepcopy(self.app_api.settings)

    def tearDown(self):
        super(TestCatInterface, self).tearDown()
        agent = newrelic.core.agent.agent_instance()
        app = agent.application(self.app_api.name)
        app._active_session.configuration = self.agent_settings

    def prepare_transaction(self, txn):
        txn.client_cross_process_id = "Meow"
        txn.start_time = 100
        txn.end_time = 200
        txn.guid = '02c574ebb384313d'
        txn.enabled = True
        txn.synthetics_header = "Wruff"
        txn._settings.cross_process_id = "1#1"
        txn._settings.encoding_key = "shhh"
        txn._settings.cross_application_tracer.enabled = True
        txn._settings.distributed_tracing.enabled = False
        txn._settings.trusted_account_ids = [1]

    def test_generate_response_without_headers(self):
        with Transaction(self.app_api) as txn:
            self.assertEqual(txn._generate_response_headers(), [])

    def test_generate_response_with_headers_data(self):
        application = newrelic.api.application.application_instance()
        with Transaction(application) as txn:
            self.prepare_transaction(txn)
            self.assertEqual(
                    txn._generate_response_headers(),
                    txn_cat_info.obfuscated_response_headers)

    def test_generate_response_using_read_length_argument(self):
        application = newrelic.api.application.application_instance()
        with Transaction(application) as txn:
            self.prepare_transaction(txn)
            response_headers = txn._generate_response_headers(1024)
            header_value = response_headers[0][1]
            encoding_key = txn._settings.encoding_key
            assert json_decode(
                    deobfuscate(header_value, encoding_key))[4] == 1024

    def test_generate_response_using_read_length_argument_0(self):
        application = newrelic.api.application.application_instance()
        with Transaction(application) as txn:
            self.prepare_transaction(txn)
            response_headers = txn._generate_response_headers(0)
            header_value = response_headers[0][1]
            encoding_key = txn._settings.encoding_key
            assert json_decode(
                    deobfuscate(header_value, encoding_key))[4] == 0

    def test_get_response_metadata_without_headers(self):
        with Transaction(self.app_api) as txn:
            assert txn.get_response_metadata() is None

    def test_get_response_metadata_with_headers(self):
        with Transaction(self.app_api) as txn:
            self.prepare_transaction(txn)
            assert (txn.get_response_metadata() in
                    txn_cat_info.incoming_response_encoded_data)

    def test_process_request_metadata_faulty_data(self):
        with Transaction(self.app_api) as txn:
            assert txn.process_request_metadata('meow') is None
            self.assertFalse(txn.is_part_of_cat)

    def test_process_request_metadata_good_data(self):
        with Transaction(self.app_api) as txn:
            self.prepare_transaction(txn)
            assert txn.process_request_metadata(
                    txn_cat_info.outgoing_encoded_data[0]) is None
            self.assertTrue(txn.is_part_of_cat)
            self.assertEqual(txn.referring_transaction_guid,
                    '02c574ebb384313d')

    def test_generate_request_headers(self):
        library = ""
        url = "cat/meow"
        with Transaction(self.app_api, enabled=True) as txn:
            self.prepare_transaction(txn)
            trace = ExternalTrace(txn, library, url)
            resp = trace.generate_request_headers(txn)
            self.assertEqual(resp, txn_cat_info.obfuscated_request_headers)
            self.assertTrue(txn.is_part_of_cat)

    def test_get_request_metadata_not_enabled(self):
        library = ""
        url = "cat/meow"
        with Transaction(self.app_api) as txn:
            self.prepare_transaction(txn)
            txn._settings.cross_application_tracer.enabled = False
            trace = ExternalTrace(txn, library, url)
            resp = trace.generate_request_headers(txn)
            self.assertEqual(resp,
                    [('X-NewRelic-Synthetics', 'Wruff')])
            self.assertFalse(txn.is_part_of_cat)

    def test_get_request_metadata_enabled(self):
        library = ""
        url = "cat/meow"
        with Transaction(self.app_api) as txn:
            self.prepare_transaction(txn)
            trace = ExternalTrace(txn, library, url)
            resp = trace.get_request_metadata(txn)
            assert resp in txn_cat_info.outgoing_encoded_data

    def test_process_response_metadata(self):
        library = ""
        url = "cat/meow"
        with Transaction(self.app_api) as txn:
            self.prepare_transaction(txn)
            trace = ExternalTrace(txn, library, url)
            assert trace.process_response_metadata(
                    txn_cat_info.incoming_response_encoded_data) is None
            self.assertEqual(len(trace.params), 3)
            self.assertEqual('1#1',
                    trace.params['cross_process_id'])
            self.assertEqual("WebTransaction/Uri/<undefined>",
                    trace.params['external_txn_name'])
            self.assertEqual('02c574ebb384313d',
                    trace.params['transaction_guid'])


if __name__ == '__main__':
    unittest.main()
