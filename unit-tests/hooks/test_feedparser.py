import unittest

import newrelic.api.web_transaction

@newrelic.api.web_transaction.wsgi_application()
def handler(environ, start_response):
    import feedparser

    data = feedparser.parse('http://blog.newrelic.com/feed/')
    data = feedparser.parse('feed:http://serverfault.com/feeds/tag/mod-wsgi')
    data = feedparser.parse('feed://feeds.feedburner.com/NewRelic')

    fp = open('/dev/null')
    data = feedparser.parse(fp)

    data = feedparser.parse('-')

class TransactionTests(unittest.TestCase):

    def test_transaction(self):
        environ = { 'REQUEST_URI': '/feedparser' }
        handler(environ, None).close()

if __name__ == '__main__':
    unittest.main()
