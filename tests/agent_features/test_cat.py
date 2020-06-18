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
This file contains a special case test for CAT. Most CAT testing is found at
`tests/cross_agent/test_cat_map.py` and
`newrelic/api/tests/test_cross_process.py`. This test does not fit either of
those spaces, the former being reserved for cross agent testing and the latter
being a unittest for the `process_response` method. Since this is a more end to
end style test, it does not fit as a unittest.
"""

import webtest

from newrelic.api.wsgi_application import wsgi_application

from testing_support.fixtures import (make_cross_agent_headers,
        override_application_settings)

ENCODING_KEY = '1234567890123456789012345678901234567890'


@wsgi_application()
def target_wsgi_application(environ, start_response):
    status_code = int(environ['PATH_INFO'].strip('/'))
    status = '%d STATUS' % status_code

    if status_code == 304:
        output = b''
        response_headers = []
    else:
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
    response = test_application.get('/200', headers=headers)
    assert 'X-NewRelic-App-Data' in response.headers


@override_application_settings(_override_settings)
def test_cat_insertion_disabled_on_304():
    headers = make_cross_agent_headers(payload, ENCODING_KEY, '1#1')
    response = test_application.get('/304', headers=headers)
    assert 'X-NewRelic-App-Data' not in response.headers
