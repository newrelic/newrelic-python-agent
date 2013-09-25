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
        # Nothing to do.

        details = proxy_details(None, None, None, None, False)

        self.assertEqual(details, None)

        # HTTP proxy.

        details = proxy_details('HOST', 1234, None, None, False)

        self.assertEqual(details, { 'http': 'http://HOST:1234' })

        # HTTPS proxy.

        details = proxy_details('HOST', 1234, None, None, True)

        self.assertEqual(details, { 'https': 'http://HOST:1234' })

        # HTTP proxy with full user credentials.

        details = proxy_details('HOST', 1234, 'USER', 'PASS', False)

        self.assertEqual(details, { 'http': 'http://USER:PASS@HOST:1234' })

        # HTTPS proxy with full user credentials.

        details = proxy_details('HOST', 1234, 'USER', 'PASS', True)

        self.assertEqual(details, { 'https': 'http://USER:PASS@HOST:1234' })

        # HTTP proxy with user name.

        details = proxy_details('HOST', 1234, 'USER', None, False)

        self.assertEqual(details, { 'http': 'http://USER@HOST:1234' })

        # HTTPS proxy with user name.

        details = proxy_details('HOST', 1234, 'USER', None, True)

        self.assertEqual(details, { 'https': 'http://USER@HOST:1234' })

        # HTTP proxy as HTTP URL including port.

        details = proxy_details('http://HOST:1234', None, None, None, False)

        self.assertEqual(details, { 'http': 'http://HOST:1234' })

        # HTTP proxy as HTTP URL with distinct port.

        details = proxy_details('http://HOST', 1234, None, None, False)

        self.assertEqual(details, { 'http': 'http://HOST:1234' })

        # HTTP proxy as HTTP URL with distinct user credentials.

        details = proxy_details('http://HOST:1234', None, 'USER', 'PASS',
                False)

        self.assertEqual(details, { 'http': 'http://USER:PASS@HOST:1234' })

        # HTTP proxy as HTTP URL including user credentials.

        details = proxy_details('http://USER:PASS@HOST:1234', None, None,
                None, False)

        self.assertEqual(details, { 'http': 'http://USER:PASS@HOST:1234' })

        # HTTPS proxy as HTTP URL.

        def run(*args):
            details = proxy_details('https://HOST:1234', None, None,
                    None, False)

        self.assertRaises(ValueError, run, ())

if __name__ == '__main__':
    unittest.main()
