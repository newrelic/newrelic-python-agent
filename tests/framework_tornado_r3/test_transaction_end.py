import threading

from newrelic.packages import six
from six.moves import http_client

from tornado_base_test import TornadoBaseTest

from _test_async_application import (ReturnFirstDivideRequestHandler,
        CallLaterRequestHandler, CancelAfterRanCallLaterRequestHandler,
        OneCallbackRequestHandler)

from tornado_fixtures import (
    tornado_validate_count_transaction_metrics,
    tornado_validate_time_transaction_metrics,
    tornado_validate_errors, tornado_validate_transaction_cache_empty)

def select_python_version(py2, py3):
    return six.PY3 and py3 or py2

class TornadoTest(TornadoBaseTest):

    # The count of 2 for the get method should be reduced to 1 after PYTHON-1851
    scoped_metrics = select_python_version(
            py2=[('Function/_test_async_application:'
                    'ReturnFirstDivideRequestHandler.do_divide', 1),
                ('Function/_test_async_application:do_divide (coroutine)', 1),
                ('Function/_test_async_application:'
                    'ReturnFirstDivideRequestHandler.get', 2),
                ('Function/_test_async_application:get (coroutine)', 1),],
            py3=[('Function/_test_async_application:'
                    'ReturnFirstDivideRequestHandler.do_divide', 1),
                ('Function/_test_async_application:ReturnFirstDivide'
                    'RequestHandler.do_divide (coroutine)', 1),
                ('Function/_test_async_application:'
                    'ReturnFirstDivideRequestHandler.get', 2),
                ('Function/_test_async_application:ReturnFirstDivide'
                    'RequestHandler.get (coroutine)', 1),])

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:ReturnFirstDivideRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_nested_coroutines(self):
        response = self.fetch_response('/return-divide/100/10/')
        expected = ReturnFirstDivideRequestHandler.RESPONSE
        self.assertEqual(response.body, expected)

    scoped_metrics = [
            ('Function/_test_async_application:'
                    'CallLaterRequestHandler.later', 1),
            ('Function/_test_async_application:'
                    'CallLaterRequestHandler.get', 1),
    ]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallLaterRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_call_at(self):
        response = self.fetch_response('/call-at')
        expected = CallLaterRequestHandler.RESPONSE
        self.assertEqual(response.body, expected)

    scoped_metrics = [('Function/_test_async_application:'
            'CallLaterRequestHandler.get', 1),]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CallLaterRequestHandler.get',
            scoped_metrics=scoped_metrics, forgone_metric_substrings=['later'])
    def test_cancel_call_at(self):
        response = self.fetch_response('/call-at/cancel')
        expected = CallLaterRequestHandler.RESPONSE
        self.assertEqual(response.body, expected)

    scoped_metrics = select_python_version(
            py2=[('Function/_test_async_application:'
                    'CancelAfterRanCallLaterRequestHandler.later', 1),
                ('Function/_test_async_application:'
                    'CancelAfterRanCallLaterRequestHandler.get', 2),
                ('Function/_test_async_application:get (coroutine)', 1),],
            py3=[('Function/_test_async_application:'
                    'CancelAfterRanCallLaterRequestHandler.later', 1),
                ('Function/_test_async_application:'
                    'CancelAfterRanCallLaterRequestHandler.get', 2),
                ('Function/_test_async_application:CancelAfterRanCallLater'
                    'RequestHandler.get (coroutine)', 1),])

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors(errors=[])
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:CancelAfterRanCallLaterRequestHandler.get',
            scoped_metrics=scoped_metrics)
    def test_cancel_call_at_after_callback_ran(self):
        response = self.fetch_response('/cancel-timer')
        expected = CancelAfterRanCallLaterRequestHandler.RESPONSE
        self.assertEqual(response.body, expected)

    scoped_metrics = [('Function/_test_async_application:'
            'OneCallbackRequestHandler.get', 1),
            ('Function/_test_async_application:'
            'OneCallbackRequestHandler.finish_callback', 1)]

    @tornado_validate_transaction_cache_empty()
    @tornado_validate_errors()
    @tornado_validate_count_transaction_metrics(
            '_test_async_application:OneCallbackRequestHandler.get',
            scoped_metrics=scoped_metrics, transaction_count=2)
    def test_two_requests_on_the_same_connection(self):
        # This tests emulates the keep-alive behavior that chrome uses

        def make_streaming_requests(server):
            conn = http_client.HTTPConnection(server)

            conn.putrequest('GET', '/one-callback')
            conn.endheaders()
            resp = conn.getresponse()
            msg = resp.read()

            conn.putrequest('GET', '/one-callback')
            conn.endheaders()
            resp = conn.getresponse()
            msg = resp.read()

            self.assertEqual(msg, OneCallbackRequestHandler.RESPONSE)
            conn.close()
            self.io_loop.add_callback(self.stop)

        server = 'localhost:%s' % self.get_http_port()
        t = threading.Thread(target=make_streaming_requests, args=(server,))
        t.start()
        self.wait(timeout=5.0)
        t.join(10.0)
