import webtest
import threading
import json

from testing_support.fixtures import override_application_settings

from newrelic.agent import (wsgi_application, get_browser_timing_header,
    get_browser_timing_footer, application_settings)

from newrelic.common.encoding_utils import deobfuscate, json_decode

@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

target_application = webtest.TestApp(target_wsgi_application)

def test_footer_attributes():
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    assert settings.browser_key
    assert settings.browser_monitoring.loader_version
    assert settings.js_agent_loader
    assert settings.js_agent_file
    assert settings.beacon
    assert settings.error_beacon

    token = '0123456789ABCDEF'
    headers = { 'Cookie': 'NRAGENT=tk=%s' % token }

    response = target_application.get('/', headers=headers)

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # We no longer are in control of the JS contents of the header so
    # just check to make sure it contains at least the magic string
    # 'NREUM'.

    assert header.find('NREUM') != -1

    # Now validate the various fields of the footer. The fields are
    # held by a JSON dictionary.

    data = json.loads(footer.split('NREUM.info=')[1])

    assert data['licenseKey'] == settings.browser_key
    assert data['applicationID'] == settings.application_id

    assert data['agent'] == settings.js_agent_file
    assert data['beacon'] == settings.beacon
    assert data['errorBeacon'] == settings.error_beacon

    assert data['applicationTime'] >= 0
    assert data['queueTime'] >= 0

    obfuscation_key = settings.license_key[:13]

    txn_name = deobfuscate(data['transactionName'], obfuscation_key)

    assert txn_name == u'WebTransaction/Uri/'

    assert data['agentToken'] == token
    assert len(data['ttGuid']) == 16

    assert 'userAttributes' not in data

_test_rum_ssl_for_http_is_none = {
    'browser_monitoring.ssl_for_http': None }

@override_application_settings(_test_rum_ssl_for_http_is_none)
def test_ssl_for_http_is_none():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is None

    response = target_application.get('/')
    footer = response.html.html.body.script.text
    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'sslForHttp' not in data

_test_rum_ssl_for_http_is_true = {
    'browser_monitoring.ssl_for_http': True }

@override_application_settings(_test_rum_ssl_for_http_is_true)
def test_ssl_for_http_is_true():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is True

    response = target_application.get('/')
    footer = response.html.html.body.script.text
    data = json.loads(footer.split('NREUM.info=')[1])

    assert data['sslForHttp'] is True

_test_rum_ssl_for_http_is_false = {
    'browser_monitoring.ssl_for_http': False }

@override_application_settings(_test_rum_ssl_for_http_is_false)
def test_ssl_for_http_is_false():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is False

    response = target_application.get('/')
    footer = response.html.html.body.script.text
    data = json.loads(footer.split('NREUM.info=')[1])

    assert data['sslForHttp'] is False
