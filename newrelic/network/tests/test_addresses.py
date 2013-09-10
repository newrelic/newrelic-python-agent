import unittest

from newrelic.network.addresses import platform_url, proxy_details

class TestAddresses(unittest.TestCase):

    def test_platform_url(self):
        url = platform_url()

        self.assertEqual(url,
                'https://platform-api.newrelic.com/platform/v1/metrics')

        url = platform_url(host='HOST')

        self.assertEqual(url,
                'https://HOST/platform/v1/metrics')

        url = platform_url(port=1234)

        self.assertEqual(url,
                'https://platform-api.newrelic.com:1234/platform/v1/metrics')

        url = platform_url(ssl=False)

        self.assertEqual(url,
                'http://platform-api.newrelic.com/platform/v1/metrics')

    def test_proxy_details(self):
        details = proxy_details(None, None, None, None, False)

        self.assertEqual(details, None)

        details = proxy_details('HOST', 1234, None, None, False)

        self.assertEqual(details, { 'http': 'HOST:1234' })

        details = proxy_details('HOST', 1234, None, None, True)

        self.assertEqual(details, { 'https': 'HOST:1234' })

        details = proxy_details('HOST', 1234, 'USER', 'PASS', False)

        self.assertEqual(details, { 'http': 'http://USER:PASS@HOST:1234' })

if __name__ == '__main__':
    unittest.main()
