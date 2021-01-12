# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.encoding_utils import obfuscate, json_encode

from testing_support.fixtures import (override_application_settings,
        override_application_name, validate_tt_parameters,
        make_cross_agent_headers, validate_analytics_catmap_data)
from testing_support.mock_external_http_server import (
        MockExternalHTTPHResponseHeadersServer)

ENCODING_KEY = '1234567890123456789012345678901234567890'
CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
JSON_DIR = os.path.normpath(os.path.join(CURRENT_DIR, 'fixtures'))
OUTBOUD_REQUESTS = {}

_parameters_list = ["name", "appName", "transactionName", "transactionGuid",
        "inboundPayload", "outboundRequests", "expectedIntrinsicFields",
        "nonExpectedIntrinsicFields"]


@pytest.fixture(scope='module')
def server():
    with MockExternalHTTPHResponseHeadersServer() as _server:
        yield _server


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
    old_cat = environ.get('old_cat') == 'True'
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

        if old_cat:
            if (expected_outbound_header !=
                    generated_outbound_header['X-NewRelic-Transaction']):
                status = '500 Outbound Headers Check Failed.'
        else:
            if 'X-NewRelic-Transaction' in generated_outbound_header:
                status = '500 Outbound Headers Check Failed.'
        r = urlopen(environ['server_url'])
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
@pytest.mark.parametrize('old_cat', (True, False))
def test_cat_map(name, appName, transactionName, transactionGuid,
        inboundPayload, outboundRequests, expectedIntrinsicFields,
        nonExpectedIntrinsicFields, old_cat, server):
    global OUTBOUD_REQUESTS
    OUTBOUD_REQUESTS = outboundRequests or {}

    _custom_settings = {
            'cross_process_id': '1#1',
            'encoding_key': ENCODING_KEY,
            'trusted_account_ids': [1],
            'cross_application_tracer.enabled': True,
            'distributed_tracing.enabled': not old_cat,
            'transaction_tracer.transaction_threshold': 0.0,
    }

    if expectedIntrinsicFields and old_cat:
        _external_node_params = {
                'path_hash': expectedIntrinsicFields['nr.pathHash'],
                'trip_id': expectedIntrinsicFields['nr.tripId'],
        }
    else:
        _external_node_params = []

    if not old_cat:
        # since no better cat headers will be generated, no intrinsics should
        # be added
        expectedIntrinsicFields = {}

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

        # Only generate old cat style headers. This will test to make sure we
        # are properly ignoring these headers when the agent is using better
        # cat.

        headers = make_cross_agent_headers(inboundPayload, ENCODING_KEY, '1#1')
        response = target_application.get('/', headers=headers,
                extra_environ={'txn': txn_name, 'guid': guid,
                    'old_cat': str(old_cat),
                    'server_url': 'http://localhost:%d' % server.port})

        # Validation of analytic data happens in the decorator.

        assert response.status == '200 OK'

        content = response.html.html.body.p.string

        # Validate actual body content as sansity check.

        assert content == 'RESPONSE'

    run_cat_test()
