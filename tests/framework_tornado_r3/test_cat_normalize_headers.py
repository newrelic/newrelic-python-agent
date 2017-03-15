import unittest
from tornado.httputil import HTTPHeaders, _NormalizedHeaderCache

class TestNRHeadersNormalization(unittest.TestCase):

    def setUp(self):
        self.headers = HTTPHeaders()
        self.nr_header = 'X-NewRelic-App-Data'
        self.nr_header_wrong = 'X-Newrelic-App-Data'

    def test_non_nr_headers_still_normalized(self):
        self.headers.add('ALL-CAPS', '')
        self.headers.add('lower-case', '')
        self.headers.add('camelCase', '')

        headers = dict(**self.headers)

        self.assertTrue('All-Caps' in headers)
        self.assertTrue('Lower-Case' in headers)
        self.assertTrue('Camelcase' in headers)

    def test_nr_headers_not_normalized(self):
        self.headers.add(self.nr_header, 'ladeeda')

        headers = dict(**self.headers)

        self.assertTrue(self.nr_header in headers)
        self.assertTrue(self.nr_header_wrong not in headers)
        self.assertEqual(headers[self.nr_header], 'ladeeda')

    def test_nr_headers_added_twice(self):
        self.headers.add(self.nr_header, 'hahaha')
        self.headers.add(self.nr_header, 'lalala')

        headers = dict(**self.headers)

        self.assertTrue(self.nr_header in headers)
        self.assertTrue(self.nr_header_wrong not in headers)
        self.assertEqual(headers[self.nr_header], 'hahaha,lalala')

    def test_get_list_nr_header(self):
        as_list = self.headers.get_list(self.nr_header)

        self.assertEqual([], as_list)

        self.headers.add(self.nr_header, 'hahaha')
        self.headers.add(self.nr_header, 'lalala')

        as_list = self.headers.get_list(self.nr_header)

        self.assertEqual(['hahaha', 'lalala'], as_list)

    def test_http_headers_setitem_normalized(self):
        self.headers['ALL-CAPS'] = ''
        self.headers['lower-case'] = ''
        self.headers['camelCase'] = ''

        headers = dict(**self.headers)

        self.assertTrue('All-Caps' in headers)
        self.assertTrue('Lower-Case' in headers)
        self.assertTrue('Camelcase' in headers)

    def test_http_headers_setitem_nr_not_normalized(self):
        self.headers[self.nr_header] = 'hohum'

        headers = dict(**self.headers)

        self.assertTrue(self.nr_header in headers)
        self.assertTrue(self.nr_header_wrong not in headers)
        self.assertEqual(headers[self.nr_header], 'hohum')

    def test_http_headers_getitem_normalized(self):
        self.headers['ALL-CAPS'] = 'abc'
        self.headers['lower-case'] = 'def'
        self.headers['camelCase'] = 'ghi'

        self.assertEqual(self.headers['ALL-CAPS'], 'abc')
        self.assertEqual(self.headers['All-Caps'], 'abc')

        self.assertEqual(self.headers['lower-case'], 'def')
        self.assertEqual(self.headers['Lower-Case'], 'def')

        self.assertEqual(self.headers['camelCase'], 'ghi')
        self.assertEqual(self.headers['Camelcase'], 'ghi')

    def test_http_headers_getitem_nr_not_normalized(self):
        self.headers[self.nr_header] = 'snoop'

        self.assertEqual(self.headers[self.nr_header], 'snoop')

    def test_http_headers_delitem_normalized(self):
        self.headers['ALL-CAPS'] = 'abc'
        self.headers['lower-case'] = 'def'
        self.headers['camelCase'] = 'ghi'

        del self.headers['ALL-CAPS']
        del self.headers['lower-case']
        del self.headers['camelCase']

        headers = dict(**self.headers)

        self.assertTrue('ALL-CAPS' not in headers)
        self.assertTrue('lower-case' not in headers)
        self.assertTrue('camelCase' not in headers)

        self.assertTrue('All-Caps' not in headers)
        self.assertTrue('Lower-Case' not in headers)
        self.assertTrue('Camelcase' not in headers)

        self.headers['ALL-CAPS'] = 'abc'
        self.headers['lower-case'] = 'def'
        self.headers['camelCase'] = 'ghi'

        del self.headers['All-Caps']
        del self.headers['Lower-Case']
        del self.headers['Camelcase']

        headers = dict(**self.headers)

        self.assertTrue('ALL-CAPS' not in headers)
        self.assertTrue('lower-case' not in headers)
        self.assertTrue('camelCase' not in headers)

        self.assertTrue('All-Caps' not in headers)
        self.assertTrue('Lower-Case' not in headers)
        self.assertTrue('Camelcase' not in headers)

    def test_http_headers_delitem_nr_not_normalized(self):
        self.headers[self.nr_header] = 'dawg'

        del self.headers[self.nr_header]

        headers = dict(**self.headers)

        self.assertTrue(self.nr_header not in headers)
        self.assertTrue(self.nr_header_wrong not in headers)

class TestNormalizedHeaderCache(unittest.TestCase):

    def setUp(self):
        self.cache = _NormalizedHeaderCache(3)
        self.nr_header = 'X-NewRelic-App-Data'
        self.nr_header_wrong = 'X-Newrelic-App-Data'

    def test_nr_hearder_not_normalized(self):
        self.cache[self.nr_header]

        cache = dict(**self.cache)

        self.assertEqual(cache[self.nr_header], self.nr_header)
        self.assertEqual(len(cache), 1)

    def test_non_nr_header_normalized(self):
        self.cache['ALL-CAPS']
        self.cache['lower-case']
        self.cache['camelCase']

        cache = dict(**self.cache)

        self.assertEqual(cache['ALL-CAPS'], 'All-Caps')
        self.assertEqual(cache['lower-case'], 'Lower-Case')
        self.assertEqual(cache['camelCase'], 'Camelcase')
