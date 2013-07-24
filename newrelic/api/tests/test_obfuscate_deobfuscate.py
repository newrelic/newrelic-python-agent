import unittest

from newrelic.api.web_transaction import obfuscate, deobfuscate

class TestCase(unittest.TestCase):

    def test_empty_string(self):
        key = '0123456789'
        string = ''

        self.assertEqual(obfuscate(string, key), '')
        self.assertEqual(deobfuscate(string, key), '')

    def test_empty_key(self):
        key = ''
        string = 'abcd'

        self.assertEqual(obfuscate(string, key), '')
        self.assertEqual(deobfuscate(string, key), '')

    def test_valid_string(self):
        key = '0123456789'
        string = 'abcd'

        self.assertEqual(obfuscate(string, key), 'UVNRVw==')
        self.assertEqual(deobfuscate('UVNRVw==', key), string)

if __name__ == '__main__':
    unittest.main()
