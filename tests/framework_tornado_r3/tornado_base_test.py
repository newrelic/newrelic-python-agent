import tornado.testing

from newrelic.agent import FunctionWrapper
from newrelic.core.stats_engine import StatsEngine

from _test_async_application import get_tornado_app

class TornadoBaseTest(tornado.testing.AsyncHTTPTestCase):

    def setUp(self):
        super(TornadoBaseTest, self).setUp()

        # We wrap record_transaction in every test because we want this wrapping
        # to happen after the one in test fixture. Also, this must be wrapped on
        # a per test basis to capture the correct instance of this class
        self.unwrapped_record_transaction = StatsEngine.record_transaction
        StatsEngine.record_transaction = FunctionWrapper(
                StatsEngine.record_transaction,
                self.stop_after_record_transaction)

        self.waits_expected = 0
        self.waits_counter = 0

    def tearDown(self):
        StatsEngine.record_transaction = self.unwrapped_record_transaction

    def get_app(self):
        return get_tornado_app()

    def get_httpserver_options(self):
        return { 'chunk_size': 250 }

    # These tests validate the server response and the data written
    # in record_transaction. Before we can validate this, we need to ensure that
    # the response has been returned and record_transaction has been called.
    # That means we can not use the default url fetch method provided by the
    # Tornado test framework but instead create our own fetch methods and the
    # associated wait/stop methods.
    def stop_after_record_transaction(self, wrapped, instance, args, kwargs):
        wrapped(*args, **kwargs)
        self.waits_counter_check()

    def fetch_finished(self, response):
        self.waits_counter_check()

    def waits_counter_check(self):
        self.waits_counter += 1;
        if self.waits_counter == self.waits_expected:
            self.stop()

    def fetch_response(self, path, is_http_error=False, **kwargs):
        # For each request we need to wait for 2 events: the response and a call
        # to record transaction.
        self.waits_expected += 2

        # Make a request to the server.
        future = self.http_client.fetch(self.get_url(path), self.fetch_finished,
                **kwargs)
        try:
            self.wait(timeout=5.0)
        except Exception as e:
            self.assertTrue(False, "Error occurred waiting for response: "
                    "%s, %s" % (type(e), e))

        # Retrieve the server response. An exception will be raised
        # if the server did not respond successfully.
        try:
            response = future.result()
        except tornado.httpclient.HTTPError as e:
            if is_http_error:
                return e.response
            else:
                raise
        else:
            self.assertFalse(is_http_error, "Client did not receive an error "
                    "though one was expected.")
            return response

    def fetch_responses(self, paths):
        # For each request we need to wait for 2 events: the response and a call
        # to record transaction.
        self.waits_expected += 2 * len(paths)
        futures = []
        for path in paths:
            futures.append(self.http_client.fetch(
                    self.get_url(path), self.fetch_finished))
        self.wait(timeout=5.0)
        responses = []
        for future in futures:
            responses.append(future.result())
        return responses

    def fetch_exception(self, path):
        # ExpectLog ensures that the expected server side exception occurs and
        # makes the logging to stdout less noisy.
        with tornado.testing.ExpectLog('tornado.application',
                "Uncaught exception GET %s" % path):
            return self.fetch_response(path, is_http_error=True)
