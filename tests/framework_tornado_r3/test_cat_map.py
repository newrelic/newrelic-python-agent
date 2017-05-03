"""
This is an implementation of the cross agent tests for cat map using a tornado
application. Another implementation of these tests using a wsgi application can
be found in test/cross_agent/test_cat_map.py
"""

import json
import os
import pytest
import sys

from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)

from testing_support.fixtures import (override_application_settings,
        override_application_name, make_cross_agent_headers,
        validate_analytics_catmap_data, validate_tt_parameters)

from tornado_base_test import TornadoBaseTest, TornadoZmqBaseTest
from _test_async_application import CatMapHandler

ENCODING_KEY = '1234567890123456789012345678901234567890'
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, '..', 'cross_agent',
    'fixtures'))

_parameters_list = ["name", "appName", "transactionName", "transactionGuid",
        "inboundPayload", "outboundRequests", "expectedIntrinsicFields",
        "nonExpectedIntrinsicFields"]


def load_tests():
    result = []
    path = os.path.join(JSON_DIR, 'cat_map.json')
    with open(path, 'r') as fh:
        tests = json.load(fh)

    for test in tests:
        values = tuple([test.get(param, None) for param in _parameters_list])
        result.append(values)

    return result


class AllTests(object):

    def setUp(self):
        super(AllTests, self).setUp()
        self.external = MockExternalHTTPHResponseHeadersServer()
        self.external.start()

    def tearDown(self):
        super(AllTests, self).tearDown()
        self.external.stop()

    def test_cat_map(self):

        for params in load_tests():
            (name, appName, transactionName, transactionGuid,
                inboundPayload, outboundRequests, expectedIntrinsicFields,
                nonExpectedIntrinsicFields) = params

            _custom_settings = {
                'cross_process_id': '1#1',
                'encoding_key': ENCODING_KEY,
                'trusted_account_ids': [1],
                'cross_application_tracer.enabled': True,
                'transaction_tracer.transaction_threshold': 0.0,
            }

            def get_test_params(handler):
                txn_name = transactionName.split('/', 3)
                return (transactionGuid, outboundRequests or [], txn_name,
                        self.external.port)
            CatMapHandler.get_test_params = get_test_params

            if expectedIntrinsicFields:
                _external_node_params = {
                    'path_hash': expectedIntrinsicFields['nr.pathHash'],
                    'trip_id': expectedIntrinsicFields['nr.tripId'],
                }
            else:
                _external_node_params = []

            @validate_tt_parameters(required_params=_external_node_params)
            @validate_analytics_catmap_data(transactionName,
                    expected_attributes=expectedIntrinsicFields,
                    non_expected_attributes=nonExpectedIntrinsicFields)
            @override_application_settings(_custom_settings)
            @override_application_name(appName)
            def run_cat_test():

                headers = make_cross_agent_headers(inboundPayload,
                        ENCODING_KEY, '1#1')

                # Test sync

                response = self.fetch_response('/cat-map/sync',
                        headers=headers)

                assert response.code == 200
                assert response.body == CatMapHandler.RESPONSE

                # Test async

                response = self.fetch_response('/cat-map/async',
                        headers=headers)

                assert response.code == 200
                assert response.body == CatMapHandler.RESPONSE

            run_cat_test()


class TornadoDefaultIOLoopTest(AllTests, TornadoBaseTest):
    pass


@pytest.mark.skipif(sys.version_info < (2, 7),
        reason='pyzmq does not support Python 2.6')
class TornadoZmqIOLoopTest(AllTests, TornadoZmqBaseTest):
    pass
