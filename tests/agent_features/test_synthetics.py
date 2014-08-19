import webtest

from newrelic.agent import wsgi_application
from newrelic.common.encoding_utils import (deobfuscate, obfuscate,
        json_decode, json_encode)

from testing_support.fixtures import (validate_synthetics_event,
        override_application_settings)

ENCODING_KEY = '1234567890123456789012345678901234567890'
ACCOUNT_ID = '444'
SYNTHETICS_RESOURCE_ID = '09845779-16ef-4fa7-b7f2-44da8e62931c'
SYNTHETICS_JOB_ID = '8c7dd3ba-4933-4cbb-b1ed-b62f511782f4'
SYNTHETICS_MONITOR_ID = 'dc452ae9-1a93-4ab5-8a33-600521e9cd00'

_override_settings = {
    'encoding_key': ENCODING_KEY,
    'trusted_account_ids': [int(ACCOUNT_ID)]
}

def make_synthetics_header(version='1', account_id=ACCOUNT_ID,
        resource_id=SYNTHETICS_RESOURCE_ID, job_id=SYNTHETICS_JOB_ID,
        monitor_id=SYNTHETICS_MONITOR_ID, encoding_key=ENCODING_KEY):
    value = [version, account_id, resource_id, job_id, monitor_id]
    value = obfuscate(json_encode(value), encoding_key)
    return {'X-NewRelic-Synthetics': value}

def decode_header(header, encoding_key=ENCODING_KEY):
    result = deobfuscate(header, encoding_key)
    return json_decode(result)

@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'

    output = '<html><head>header</head><body><p>RESPONSE</p></body></html>'
    output = output.encode('UTF-8')

    response_headers = [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

target_application = webtest.TestApp(target_wsgi_application)

_test_valid_synthetics_event_required = [
        ('nr.syntheticsResourceId', SYNTHETICS_RESOURCE_ID),
        ('nr.syntheticsJobId', SYNTHETICS_JOB_ID),
        ('nr.syntheticsMonitorId', SYNTHETICS_MONITOR_ID)]
_test_valid_synthetics_event_forgone = []

@validate_synthetics_event(_test_valid_synthetics_event_required,
        _test_valid_synthetics_event_forgone, should_exist=True)
@override_application_settings(_override_settings)
def test_valid_synthetics_event():
    headers = make_synthetics_header()
    response = target_application.get('/', headers=headers)

@validate_synthetics_event([], [], should_exist=False)
@override_application_settings(_override_settings)
def test_no_synthetics_event_unsupported_version():
    headers = make_synthetics_header(version='0')
    response = target_application.get('/', headers=headers)

@validate_synthetics_event([], [], should_exist=False)
@override_application_settings(_override_settings)
def test_no_synthetics_event_untrusted_account():
    headers = make_synthetics_header(account_id='999')
    response = target_application.get('/', headers=headers)

@validate_synthetics_event([], [], should_exist=False)
@override_application_settings(_override_settings)
def test_no_synthetics_event_mismatched_encoding_key():
    encoding_key = 'zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'
    headers = make_synthetics_header(encoding_key=encoding_key)
    response = target_application.get('/', headers=headers)

@validate_synthetics_event(_test_valid_synthetics_event_required,
        [], should_exist=True)
@override_application_settings(_override_settings)
def test_valid_synthetics_response_header():
    headers = make_synthetics_header()
    response = target_application.get('/', headers=headers)

    assert 'X-NewRelic-App-Data' in response.headers
    header = response.headers['X-NewRelic-App-Data']
    header = deobfuscate(header, _override_settings['encoding_key'])
    header = json_decode(header)

    assert len(header) == 7

    # Don't know how to check if the guid in the header is the same guid
    # that was generated in the transaction, so I'll just make sure it
    # looks like a guid.

    assert len(header[5]) == 16     # 16 chars
    assert int(header[5], 16)       # Hex chars

@validate_synthetics_event([], [], should_exist=False)
@override_application_settings(_override_settings)
def test_no_synthetics_response_header():
    headers = make_synthetics_header(account_id='999')
    response = target_application.get('/', headers=headers)
    assert 'X-NewRelic-App-Data' not in response.headers
