import unittest

from newrelic.common.encoding_utils import obfuscate, deobfuscate

class TestCase(unittest.TestCase):

    def test_empty_string(self):
        key = '0123456789'
        string = ''

        self.assertEqual(obfuscate(string, key), '')
        self.assertEqual(deobfuscate(string, key), '')
        self.assertEqual(type(obfuscate(string, key)), type(''))

    def test_empty_key(self):
        key = ''
        string = 'abcd'

        self.assertEqual(obfuscate(string, key), '')
        self.assertEqual(deobfuscate(string, key), '')
        self.assertEqual(type(obfuscate(string, key)), type(''))

    def test_valid_string(self):
        key = '0123456789'
        string = 'abcd'
        result = 'UVNRVw=='

        self.assertEqual(obfuscate(string, key), result)
        self.assertEqual(deobfuscate(result, key), string)
        self.assertEqual(type(obfuscate(string, key)), type(result))

if __name__ == '__main__':
    unittest.main()
