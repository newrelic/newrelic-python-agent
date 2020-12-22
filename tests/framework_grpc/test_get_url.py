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

import grpc
import grpc._channel
import pytest

from newrelic.hooks.framework_grpc import _get_uri_method


_test_get_url_unary_unary = [
        ('localhost:1234', '/sample/method',
            'grpc://localhost:1234/sample/method'),
        ('localhost:1234', 'method/without/leading/slash',
            'grpc://localhost:1234/method/without/leading/slash'),
        ('localhost', '/no/port',
            'grpc://localhost/no/port'),
]

_test_channel_types = [
        ('unary_unary', grpc._channel._UnaryUnaryMultiCallable),
        ('unary_stream', grpc._channel._UnaryStreamMultiCallable),
        ('stream_unary', grpc._channel._StreamUnaryMultiCallable),
        ('stream_stream', grpc._channel._StreamStreamMultiCallable),
]


@pytest.mark.parametrize('url,method,expected', _test_get_url_unary_unary)
@pytest.mark.parametrize('channel_type,channel_class', _test_channel_types)
def test_get_url_method(url, method, expected, channel_type,
        channel_class):
    channel = grpc.insecure_channel(url)
    unary_unary = getattr(channel, channel_type)(method)
    assert type(unary_unary) == channel_class

    actual_url, actual_method = _get_uri_method(unary_unary)
    assert actual_url == expected
    assert actual_method == method.lstrip('/')
