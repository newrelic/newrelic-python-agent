import grpc
import grpc._channel
import pytest

from newrelic.hooks.external_grpc import _get_uri


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
def test_get_url(url, method, expected, channel_type,
        channel_class):
    channel = grpc.insecure_channel(url)
    unary_unary = getattr(channel, channel_type)(method)
    assert type(unary_unary) == channel_class

    actual = _get_uri(unary_unary)
    assert actual == expected
