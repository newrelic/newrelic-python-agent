import unittest

from newrelic.common.encoding_utils import (decode_newrelic_header, obfuscate,
        json_encode)


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
