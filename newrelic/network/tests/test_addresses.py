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

        details = proxy_details(None, None, None, None, None)

        self.assertEqual(details, None)

        def proxy_map(url):
            return { 'http': url, 'https': url }

        # HTTP proxy scheme.

        details = proxy_details('http', 'HOST', 1234, None, None)

        self.assertEqual(details, proxy_map('http://HOST:1234'))

        # HTTPS proxy scheme.

        details = proxy_details('https', 'HOST', 1234, None, None)

        self.assertEqual(details, proxy_map('https://HOST:1234'))

        # No proxy scheme.

        details = proxy_details(None, 'HOST', 1234, None, None)

        self.assertEqual(details, proxy_map('http://HOST:1234'))

        # HTTP proxy scheme with full user credentials.

        details = proxy_details('http', 'HOST', 1234, 'USER', 'PASS')

        self.assertEqual(details, proxy_map('http://USER:PASS@HOST:1234'))

        # HTTPS proxy scheme with full user credentials.

        details = proxy_details('https', 'HOST', 1234, 'USER', 'PASS')

        self.assertEqual(details, proxy_map('https://USER:PASS@HOST:1234'))

        # HTTP proxy scheme with user name.

        details = proxy_details('http', 'HOST', 1234, 'USER', None)

        self.assertEqual(details, proxy_map('http://USER@HOST:1234'))

        # HTTPS proxy scheme with user name.

        details = proxy_details('https', 'HOST', 1234, 'USER', None)

        self.assertEqual(details, proxy_map('https://USER@HOST:1234'))

        # HTTP proxy scheme as HTTP URL including port.

        details = proxy_details('http', 'http://HOST:1234', None, None, None)

        self.assertEqual(details, proxy_map('http://HOST:1234'))

        # HTTP proxy scheme as HTTP URL with distinct port.

        details = proxy_details('http', 'http://HOST', 1234, None, None)

        self.assertEqual(details, proxy_map('http://HOST:1234'))

        # HTTP proxy scheme as HTTP URL with distinct user credentials.

        details = proxy_details('http', 'http://HOST:1234', None, 'USER',
                'PASS')

        self.assertEqual(details, proxy_map('http://USER:PASS@HOST:1234'))

        # HTTP proxy scheme as HTTP URL including user credentials.

        details = proxy_details('http', 'http://USER:PASS@HOST:1234', None,
                None, None)

        self.assertEqual(details, proxy_map('http://USER:PASS@HOST:1234'))

        # HTTPS proxy scheme as HTTPS URL including port.

        details = proxy_details('http', 'https://HOST:1234', None, None, None)

        self.assertEqual(details, proxy_map('https://HOST:1234'))

        # HTTPS proxy scheme as HTTPS URL with distinct port.

        details = proxy_details('http', 'https://HOST', 1234, None, None)

        self.assertEqual(details, proxy_map('https://HOST:1234'))

        # HTTPS proxy scheme as HTTPS URL with distinct user credentials.

        details = proxy_details('http', 'https://HOST:1234', None, 'USER',
                'PASS')

        self.assertEqual(details, proxy_map('https://USER:PASS@HOST:1234'))

        # HTTPS proxy scheme as HTTPS URL including user credentials.

        details = proxy_details('http', 'https://USER:PASS@HOST:1234', None,
                None, None)

        self.assertEqual(details, proxy_map('https://USER:PASS@HOST:1234'))

if __name__ == '__main__':
    unittest.main()
