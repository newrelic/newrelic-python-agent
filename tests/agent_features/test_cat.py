"""
This file contains a special case test for CAT. Most CAT testing is found at
`tests/cross_agent/test_cat_map.py` and
`newrelic/api/tests/test_cross_process.py`. This test does not fit either of
those spaces, the former being reserved for cross agent testing and the latter
being a unittest for the `process_response` method. Since this is a more end to
end style test, it does not fit as a unittest.
"""

import webtest

from newrelic.agent import wsgi_application

from testing_support.fixtures import (make_cross_agent_headers,
        override_application_settings)

ENCODING_KEY = '1234567890123456789012345678901234567890'

@wsgi_application()
def target_wsgi_application(environ, start_response):
    status = '200 OK'

    output = b'hello world'
    response_headers = [('Content-type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

test_application = webtest.TestApp(target_wsgi_application)

_override_settings = {
    'cross_process_id': '1#1',
    'encoding_key': ENCODING_KEY,
    'trusted_account_ids': [1],
    'browser_monitoring.enabled': False,
}

payload = ['b854df4feb2b1f06', False, '7e249074f277923d', '5d2957be']

@override_application_settings(_override_settings)
def test_cat_disabled_browser_monitoring():
    headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')
    response = test_application.get('/', headers=headers)
    assert 'X-NewRelic-App-Data' in response.headers
