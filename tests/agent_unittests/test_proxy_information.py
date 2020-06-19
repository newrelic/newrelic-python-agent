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

from newrelic.core.config import global_settings
from newrelic.core.data_collector import proxy_server, connection_type

import pytest

_connection_combinations = (
    (None, None, None, 'direct/https'),
    (None, 'http://localhost:8888', None, 'http-proxy/https'),
    (None, 'https://localhost:8888', None, 'https-proxy/https'),
    (None, 'localhost', 8888, 'https-proxy/https'),
    ('http', 'localhost', 8888, 'http-proxy/https'),
    ('https', 'localhost', 8888, 'https-proxy/https'),
)

@pytest.mark.parametrize(('proxy_scheme', 'proxy_host', 'proxy_port',
        'expected'), _connection_combinations)
def test_connection_type(proxy_scheme, proxy_host, proxy_port, expected):
    settings = global_settings()

    original_proxy_scheme = settings.proxy_scheme
    original_proxy_host = settings.proxy_host
    original_proxy_port = settings.proxy_port

    settings.proxy_scheme = proxy_scheme
    settings.proxy_host = proxy_host
    settings.proxy_port = proxy_port

    try:
        proxies = proxy_server()
        type = connection_type(proxies)
        assert type == expected

    finally:
        settings.proxy_scheme = original_proxy_scheme
        settings.proxy_host = original_proxy_host
        settings.proxy_port = original_proxy_port
