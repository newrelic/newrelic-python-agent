import unittest

from newrelic.common.encoding_utils import (decode_newrelic_header, obfuscate,
        json_encode, ensure_utf8)


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

    def test_ensure_utf8_unicode(self):
        unicode_input = u'test_input'

        result = ensure_utf8(unicode_input)
        self.assertEqual(result, unicode_input)

    def test_ensure_utf8_bytes(self):
        bytes_input = b'test_input'
        output = bytes_input.decode('utf-8')

        result = ensure_utf8(bytes_input)
        self.assertEqual(result, output)

    def test_ensure_utf8_bytearray(self):
        bytes_input = bytearray('test_input', 'utf-8')
        output = bytes_input.decode('utf-8')

        result = ensure_utf8(bytes_input)
        self.assertEqual(result, output)

    def test_ensure_utf8_string(self):
        str_input = 'test_input'

        result = ensure_utf8(str_input)
        self.assertEqual(result, str_input)

    def test_ensure_utf8_cp424(self):
        assert ensure_utf8('test'.encode('cp424')) is None

    def test_ensure_utf8_none(self):
        assert ensure_utf8(None) is None


if __name__ == '__main__':
    unittest.main()
