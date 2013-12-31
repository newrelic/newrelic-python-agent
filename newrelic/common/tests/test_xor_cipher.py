import unittest

from newrelic.common.encoding_utils import (xor_cipher_genkey,
        xor_cipher_encrypt, xor_cipher_decrypt, xor_cipher_encrypt_base64,
        xor_cipher_decrypt_base64)

class TestCase(unittest.TestCase):

    def test_xor_cipher_genkey_no_length(self):
        result = xor_cipher_genkey('0123456789')
        self.assertEqual(result, bytearray(b'0123456789'))

        result = xor_cipher_genkey(u'0123456789')
        self.assertEqual(result, bytearray(b'0123456789'))

    def test_xor_cipher_genkey_with_length(self):
        result = xor_cipher_genkey('0123456789', 5)
        self.assertEqual(result, bytearray(b'01234'))

        result = xor_cipher_genkey(u'0123456789', 5)
        self.assertEqual(result, bytearray(b'01234'))

    def test_xor_cipher_encrypt_empty_string(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt('', key)
        self.assertEqual(result, bytearray(b''))

        result = xor_cipher_encrypt(u'', key)
        self.assertEqual(result, bytearray(b''))

    def test_xor_cipher_encrypt_same_length_as_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt('abcdefghij', key)
        self.assertEqual(result, bytearray(b'QSQWQSQ_QS'))

        result = xor_cipher_encrypt(u'abcdefghij', key)
        self.assertEqual(result, bytearray(b'QSQWQSQ_QS'))

    def test_xor_cipher_encrypt_longer_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt('abcd', key)
        self.assertEqual(result, bytearray(b'QSQW'))

        result = xor_cipher_encrypt(u'abcd', key)
        self.assertEqual(result, bytearray(b'QSQW'))

    def test_xor_cipher_encrypt_shorter_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt('abcdefghijkl', key)
        self.assertEqual(result, bytearray(b'QSQWQSQ_QS[]'))

        result = xor_cipher_encrypt(u'abcdefghijkl', key)
        self.assertEqual(result, bytearray(b'QSQWQSQ_QS[]'))

    def test_xor_cipher_decrypt_empty_string(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt(bytearray(b''), key)
        self.assertEqual(result, bytearray(b''))

        result = xor_cipher_decrypt(bytearray(b''), key)
        self.assertEqual(result, bytearray(b''))

    def test_xor_cipher_decrypt_same_length_as_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt(bytearray(b'QSQWQSQ_QS'), key)
        self.assertEqual(result, bytearray(b'abcdefghij'))

    def test_xor_cipher_decrypt_longer_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt(bytearray(b'QSQW'), key)
        self.assertEqual(result, bytearray(b'abcd'))

    def test_xor_cipher_decrypt_shorter_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt(bytearray(b'QSQWQSQ_QS[]'), key)
        self.assertEqual(result, bytearray(b'abcdefghijkl'))

    def test_xor_cipher_encrypt_base64_empty_string(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt_base64(b'', key)
        self.assertEqual(result, u'')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64('', key)
        self.assertEqual(result, u'')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64(u'', key)
        self.assertEqual(result, u'')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_empty_string(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt_base64(b'', key)
        self.assertTrue(result is u'')

        result = xor_cipher_decrypt_base64('', key)
        self.assertTrue(result is u'')

        result = xor_cipher_decrypt_base64(u'', key)
        self.assertTrue(result is u'')

    def test_xor_cipher_encrypt_base64_same_length_as_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt_base64(b'abcdefghij', key)
        self.assertEqual(result, u'UVNRV1FTUV9RUw==')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64('abcdefghij', key)
        self.assertEqual(result, u'UVNRV1FTUV9RUw==')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64(u'abcdefghij', key)
        self.assertEqual(result, u'UVNRV1FTUV9RUw==')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_same_length_as_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt_base64(b'UVNRV1FTUV9RUw==', key)
        self.assertTrue(result, u'abcdefghij')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64('UVNRV1FTUV9RUw==', key)
        self.assertTrue(result, u'abcdefghij')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64(u'UVNRV1FTUV9RUw==', key)
        self.assertTrue(result, u'abcdefghij')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_encrypt_base64_auto_genkey(self):
        key = '0123456789'

        result = xor_cipher_encrypt_base64(b'abcdefghij', key)
        self.assertEqual(result, u'UVNRV1FTUV9RUw==')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64('abcdefghij', key)
        self.assertEqual(result, u'UVNRV1FTUV9RUw==')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64(u'abcdefghij', key)
        self.assertEqual(result, u'UVNRV1FTUV9RUw==')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_auto_genkey(self):
        key = '0123456789'

        result = xor_cipher_decrypt_base64(b'UVNRV1FTUV9RUw==', key)
        self.assertTrue(result, u'abcdefghij')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64('UVNRV1FTUV9RUw==', key)
        self.assertTrue(result, u'abcdefghij')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64(u'UVNRV1FTUV9RUw==', key)
        self.assertTrue(result, u'abcdefghij')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_encrypt_base64_longer_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt_base64(b'abcd', key)
        self.assertEqual(result, u'UVNRVw==')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64('abcd', key)
        self.assertEqual(result, u'UVNRVw==')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64(u'abcd', key)
        self.assertEqual(result, u'UVNRVw==')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_longer_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt_base64(b'UVNRVw==', key)
        self.assertTrue(result, u'abcd')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64('UVNRVw==', key)
        self.assertTrue(result, u'abcd')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64(u'UVNRVw==', key)
        self.assertTrue(result, u'abcd')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_encrypt_base64_shorter_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt_base64(b'abcdefghijkl', key)
        self.assertEqual(result, u'UVNRV1FTUV9RU1td')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64('abcdefghijkl', key)
        self.assertEqual(result, u'UVNRV1FTUV9RU1td')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_encrypt_base64(u'abcdefghijkl', key)
        self.assertEqual(result, u'UVNRV1FTUV9RU1td')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_shorter_key(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt_base64(b'UVNRV1FTUV9RU1td', key)
        self.assertTrue(result, u'abcdefghijkl')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64('UVNRV1FTUV9RU1td', key)
        self.assertTrue(result, u'abcdefghijkl')
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64(u'UVNRV1FTUV9RU1td', key)
        self.assertTrue(result, u'abcdefghijkl')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_encrypt_base64_multibyte_unicode_characters(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt_base64(b'\xe2\x88\x9a'.decode('utf-8'), key)
        self.assertEqual(result, u'0rmo')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_multibyte_unicode_characters(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt_base64(b'0rmo', key)
        self.assertTrue(result, b'\xe2\x88\x9a'.decode('utf-8'))
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64('0rmo', key)
        self.assertTrue(result, b'\xe2\x88\x9a'.decode('utf-8'))
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64(u'0rmo', key)
        self.assertTrue(result, b'\xe2\x88\x9a'.decode('utf-8'))
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_encrypt_base64_invalid_utf8_byte_string(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_encrypt_base64(b'\xe2', key)
        self.assertEqual(result, u'85M=')
        self.assertEqual(type(result), type(u''))

    def test_xor_cipher_decrypt_base64_invalid_utf8_byte_string(self):
        key = xor_cipher_genkey('0123456789')

        result = xor_cipher_decrypt_base64(b'85M=', key)
        self.assertTrue(result, b'\xe2'.decode('latin-1'))
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64('85M=', key)
        self.assertTrue(result, b'\xe2'.decode('latin-1'))
        self.assertEqual(type(result), type(u''))

        result = xor_cipher_decrypt_base64(u'85M=', key)
        self.assertTrue(result, b'\xe2'.decode('latin-1'))
        self.assertEqual(type(result), type(u''))

if __name__ == '__main__':
    unittest.main()
