import unittest
import pytest
import newrelic.packages.six as six

from newrelic.common.encoding_utils import (decode_newrelic_header, obfuscate,
        json_encode, ensure_str, W3CTraceParent)


ENCODING_KEY = '1234567890123456789012345678901234567890'


class EncodingUtilsTests(unittest.TestCase):

    def test_decode_newrelic_header_invalid(self):
        decoded = decode_newrelic_header('oopsie', ENCODING_KEY)
        assert decoded is None

    def test_decode_newrelic_header_valid(self):
        payload = ['9323dc260548ed0e', False, '9323dc260548ed0e', '3b0939af']
        header = obfuscate(json_encode(payload), ENCODING_KEY)
        assert decode_newrelic_header(header, ENCODING_KEY) == payload

    def test_decode_newrelic_header_none(self):
        assert decode_newrelic_header(None, ENCODING_KEY) is None

    def test_decode_newrelic_header_encoding_key_none(self):
        payload = ['9323dc260548ed0e', False, '9323dc260548ed0e', '3b0939af']
        header = obfuscate(json_encode(payload), ENCODING_KEY)
        assert decode_newrelic_header(header, None) is None

    def test_ensure_str_unicode(self):
        unicode_input = u'test_input'

        result = ensure_str(unicode_input)
        self.assertEqual(result, unicode_input)

    def test_ensure_str_bytes(self):
        bytes_input = b'test_input'
        output = bytes_input.decode('utf-8')

        result = ensure_str(bytes_input)
        self.assertEqual(result, output)

    def test_ensure_str_bytearray(self):
        bytes_input = bytearray('test_input', 'utf-8')
        output = bytes_input.decode('utf-8')

        result = ensure_str(bytes_input)
        self.assertEqual(result, output)

    @pytest.mark.skipif(six.PY2,
            reason='cp424 is bytes in PY3 but str in PY2, so skip')
    def test_ensure_str_cp424(self):
        assert ensure_str('test'.encode('cp424')) is None

    def test_ensure_str_string(self):
        str_input = 'test_input'

        result = ensure_str(str_input)
        self.assertEqual(result, str_input)

    def test_ensure_str_none(self):
        assert ensure_str(None) is None


@pytest.mark.parametrize('payload,valid', (
    ('00-11111111111111111111111111111111-2222222222222222-1', False),
    ('000-11111111111111111111111111111111-2222222222222222-01', False),
    ('00-111111111111111111111111111111111-2222222222222222-01', False),
    ('00-11111111111111111111111111111111-22222222222222222-01', False),
    ('00-11111111111111111111111111111111-2222222222222222-001', False),
    ('00-11111111111111111111111111111111-0000000000000000-01', False),
    ('00-00000000000000000000000000000000-1111111111111111-01', False),
    ('ff-11111111111111111111111111111111-2222222222222222-01', False),
    ('00-CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC-2222222222222222-01', False),
    ('00-11111111111111111111111111111111-CCCCCCCCCCCCCCCC-01', False),
    ('00-11111111111111111111111111111111-2222222222222222-CC', False),
    ('CC-11111111111111111111111111111111-2222222222222222-01', False),
    ('00-11111111111111111111111111111111-2222222222222222101', False),
    ('00-11111111111111111111111111111111-2222222222222222-01-1', False),
    ('00-11111111111111111111111111111111-2222222222222222-01', True),
    ('cc-11111111111111111111111111111111-2222222222222222-01', True),
    ('01-11111111111111111111111111111111-2222222222222222-01-1', True),
))
def test_traceparent_decode(payload, valid):
    if valid:
        expected = {
            'tr': '11111111111111111111111111111111',
            'id': '2222222222222222',
        }
    else:
        expected = None

    assert W3CTraceParent.decode(payload) == expected


if __name__ == '__main__':
    unittest.main()
