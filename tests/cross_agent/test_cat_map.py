"""
This is an implementation of the cross agent tests for cat map using a wsgi
application. Another implementation of these tests using a tornado application
can be found in test/framework_tornado_r3/test_cat_map.py
"""

import webtest
import pytest
import json
import os

try:
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

from newrelic.packages import six

from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import (get_browser_timing_header,
        set_transaction_name, get_browser_timing_footer, set_background_task,
        current_transaction)
from newrelic.api.web_transaction import wsgi_application
from newrelic.common.encoding_utils import obfuscate, json_encode

from testing_support.fixtures import (override_application_settings,
        override_application_name, validate_tt_parameters,
        make_cross_agent_headers, validate_analytics_catmap_data)

ENCODING_KEY = '1234567890123456789012345678901234567890'
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures'))
OUTBOUD_REQUESTS = {}

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


_parameters = ",".join(_parameters_list)


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'

    txn_name = environ.get('txn')
    if six.PY2:
        txn_name = txn_name.decode('UTF-8')
    txn_name = txn_name.split('/', 3)

    guid = environ.get('guid')
    txn = current_transaction()

    txn.guid = guid
    for req in OUTBOUD_REQUESTS:
        # Change the transaction name before making an outbound call.
        outgoing_name = req['outboundTxnName'].split('/', 3)
        if outgoing_name[0] != 'WebTransaction':
            set_background_task(True)

        set_transaction_name(outgoing_name[2], group=outgoing_name[1])

        expected_outbound_header = obfuscate(
                json_encode(req['expectedOutboundPayload']), ENCODING_KEY)
        generated_outbound_header = dict(
                ExternalTrace.generate_request_headers(txn))

        # A 500 error is returned because 'assert' statements in the wsgi app
        # are ignored.

        if (expected_outbound_header !=
                generated_outbound_header['X-NewRelic-Transaction']):
            status = '500 Outbound Headers Check Failed.'
        r = urlopen('http://www.example.com')
        r.read(10)

    # Set the final transaction name.

    if txn_name[0] != 'WebTransaction':
        set_background_task(True)
    set_transaction_name(txn_name[2], group=txn_name[1])

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


target_application = webtest.TestApp(target_wsgi_application)


@pytest.mark.parametrize(_parameters, load_tests())
def test_cat_map(name, appName, transactionName, transactionGuid,
        inboundPayload, outboundRequests, expectedIntrinsicFields,
        nonExpectedIntrinsicFields):
    global OUTBOUD_REQUESTS
    OUTBOUD_REQUESTS = outboundRequests or {}

    _custom_settings = {
            'cross_process_id': '1#1',
            'encoding_key': ENCODING_KEY,
            'trusted_account_ids': [1],
            'cross_application_tracer.enabled': True,
            'transaction_tracer.transaction_threshold': 0.0,
    }

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

        if six.PY2:
            txn_name = transactionName.encode('UTF-8')
            guid = transactionGuid.encode('UTF-8')
        else:
            txn_name = transactionName
            guid = transactionGuid

        headers = make_cross_agent_headers(inboundPayload, ENCODING_KEY, '1#1')
        response = target_application.get('/', headers=headers,
                extra_environ={'txn': txn_name, 'guid': guid})

        # Validation of analytic data happens in the decorator.

        assert response.status == '200 OK'

        content = response.html.html.body.p.text

        # Validate actual body content as sansity check.

        assert content == 'RESPONSE'

    run_cat_test()
