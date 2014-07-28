import webtest
import json

from testing_support.fixtures import override_application_settings

from newrelic.agent import (wsgi_application, get_browser_timing_header,
    get_browser_timing_footer, application_settings)

from newrelic.common.encoding_utils import deobfuscate, json_decode

@wsgi_application()
def target_wsgi_application_manual_rum(environ, start_response):
    status = '200 OK'

    text = '<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>'

    output = (text % (get_browser_timing_header(),
            get_browser_timing_footer())).encode('UTF-8')

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

target_application_manual_rum = webtest.TestApp(target_wsgi_application_manual_rum)

_test_footer_attributes = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': False,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_footer_attributes)
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

    response = target_application_manual_rum.get('/', headers=headers)

    header = response.html.html.head.script.text
    content = response.html.html.body.p.text
    footer = response.html.html.body.script.text

    # Validate actual body content as sansity check.

    assert content == 'RESPONSE'

    # Validate the insertion of RUM header.

    assert header.find('NREUM HEADER') != -1

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

    assert type(data['transactionName']) == type(u'')

    txn_name = deobfuscate(data['transactionName'], obfuscation_key)

    assert txn_name == u'WebTransaction/Uri/'

    assert data['agentToken'] == token
    assert len(data['ttGuid']) == 16

    assert 'userAttributes' not in data

_test_rum_ssl_for_http_is_none = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': False,
    'browser_monitoring.ssl_for_http': None,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_rum_ssl_for_http_is_none)
def test_ssl_for_http_is_none():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is None

    response = target_application_manual_rum.get('/')
    footer = response.html.html.body.script.text
    data = json.loads(footer.split('NREUM.info=')[1])

    assert 'sslForHttp' not in data

_test_rum_ssl_for_http_is_true = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': False,
    'browser_monitoring.ssl_for_http': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_rum_ssl_for_http_is_true)
def test_ssl_for_http_is_true():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is True

    response = target_application_manual_rum.get('/')
    footer = response.html.html.body.script.text
    data = json.loads(footer.split('NREUM.info=')[1])

    assert data['sslForHttp'] is True

_test_rum_ssl_for_http_is_false = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': False,
    'browser_monitoring.ssl_for_http': False,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_rum_ssl_for_http_is_false)
def test_ssl_for_http_is_false():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is False

    response = target_application_manual_rum.get('/')
    footer = response.html.html.body.script.text
    data = json.loads(footer.split('NREUM.info=')[1])

    assert data['sslForHttp'] is False

@wsgi_application()
def target_wsgi_application_yield_single_no_head(environ, start_response):
    status = '200 OK'

    output = b'<html><body><p>RESPONSE</p></body></html>'

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    yield output

target_application_yield_single_no_head = webtest.TestApp(
        target_wsgi_application_yield_single_no_head)

_test_html_insertion_yield_single_no_head_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_yield_single_no_head_settings)
def test_html_insertion_yield_single_no_head():
    response = target_application_yield_single_no_head.get('/', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')

@wsgi_application()
def target_wsgi_application_yield_multi_no_head(environ, start_response):
    status = '200 OK'

    output = [ b'<html>', b'<body><p>RESPONSE</p></body></html>' ]

    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(b''.join(output))))]
    start_response(status, response_headers)

    for data in output:
        yield data

target_application_yield_multi_no_head = webtest.TestApp(
        target_wsgi_application_yield_multi_no_head)

_test_html_insertion_yield_multi_no_head_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_yield_multi_no_head_settings)
def test_html_insertion_yield_multi_no_head():
    response = target_application_yield_multi_no_head.get('/', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')
