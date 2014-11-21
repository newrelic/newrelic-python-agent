import webtest
import pytest
import json
import os
try:
    from urllib2 import urlopen  # Py2.X
except ImportError:
    from urllib.request import urlopen   # Py3.X

from newrelic.api.external_trace import ExternalTrace
from newrelic.packages import six
from newrelic.agent import (get_browser_timing_header, set_transaction_name,
        get_browser_timing_footer, wsgi_application, set_background_task,
        transient_function_wrapper, current_transaction)
from newrelic.common.encoding_utils import (obfuscate, json_encode)
from testing_support.fixtures import (override_application_settings,
        override_application_name, validate_tt_parameters)

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

def validate_analytics_catmap_data(name, expected_attributes=(),
        non_expected_attributes=()):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'SampledDataSet.add')
    def _validate_analytics_sample_data(wrapped, instance, args, kwargs):
        def _bind_params(sample, *args, **kwargs):
            return sample

        sample = _bind_params(*args, **kwargs)

        assert isinstance(sample, list)
        assert len(sample) == 2

        record, params = sample

        assert record['type'] == 'Transaction'
        assert record['name'] == name
        assert record['timestamp'] >= 0.0
        assert record['duration'] >= 0.0

        for key, value in expected_attributes.items():
            assert record[key] == value

        for key in non_expected_attributes:
            assert record.get(key) is None

        return wrapped(*args, **kwargs)

    return _validate_analytics_sample_data

def _make_headers(payload):
    value = obfuscate(json_encode(payload), ENCODING_KEY)
    id_value = obfuscate('1#1', ENCODING_KEY)
    return {'X-NewRelic-Transaction': value, 'X-NewRelic-ID': id_value}

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
                'nr.path_hash': expectedIntrinsicFields['nr.pathHash'],
                'nr.trip_id': expectedIntrinsicFields['nr.tripId'],
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

        response = target_application.get('/',
                headers=_make_headers(inboundPayload),
                extra_environ={'txn': txn_name,
                    'guid': guid})

        # Validation of analytic data happens in the decorator.

        assert response.status == '200 OK'

        content = response.html.html.body.p.text

        # Validate actual body content as sansity check.

        assert content == 'RESPONSE'

    run_cat_test()
