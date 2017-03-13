"""Tests to confirm that the agent's WSGI application wrappers
are "self-closing", and are not dependent on the outer WSGI
middleware or server calling close().

If the outer WSGI middleware/server consumes the entire iterable,
our wrapper will call close() automatically and close the transaction.

Or, if the outer WSGI middleware/server calls close() before consuming
the entire iterable, our wrapper will also close the transaction.

However, if the outer WSGI middleware/server fails to consume the
entire iterable, and also fails to call close(), then we are unable
to close the transaction.
"""

import unittest

import newrelic.tests.test_cases

from newrelic.api.web_transaction import (current_transaction,
        WSGIApplicationWrapper)


class Application(object):

    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]

    def __init__(self):
        self.close_called = False

    def __call__(self, environ, start_response):
        start_response(self.status, self.response_headers)
        return self

    def __iter__(self):
        yield b'Hello'
        yield b' World'

    def close(self):
        self.close_called = True


class BrokenMiddleware(object):

    def __init__(self, app):
        self.wrapped_app = app

    def __call__(self, environ, start_response):
        self.iterable = self.wrapped_app(environ, start_response)
        return self

    def __iter__(self):
        for data in self.iterable:
            yield data

    def close(self):
        # NOTE: No call to underlying self.iterable.close()!
        pass


def run_app(wsgi_app):
    """Calls the WSGI application the "right" way:

        1. Consumes entire iterable.
        2. Calls close() when finished.
    """

    environ = {}

    def start_response(status, response_headers):
        pass

    instance = wsgi_app(environ, start_response)
    response = []

    try:
        for data in instance:
            response.append(data)
    except Exception:
        raise
    else:
        return b''.join(response)
    finally:
        instance.close()


class TestWSGIMiddleware(newrelic.tests.test_cases.TestCase):

    def test_app(self):
        app = Application()
        self.assertFalse(app.close_called)

        response = run_app(app)
        self.assertTrue(app.close_called)
        self.assertEqual(response, b'Hello World')

    def test_app_wrapped_consume_all_close_transaction(self):
        app = Application()
        wrapped_app = WSGIApplicationWrapper(app)
        self.assertFalse(app.close_called)

        response = run_app(wrapped_app)
        self.assertTrue(app.close_called)
        self.assertEqual(response, b'Hello World')
        self.assertEqual(current_transaction(), None)

    def test_app_wrapped_consume_some_close_transaction(self):
        app = Application()
        wrapped_app = WSGIApplicationWrapper(app)
        target_app = wrapped_app
        self.assertFalse(app.close_called)

        environ = {}

        def start_response(status, response_headers):
            pass

        instance = target_app(environ, start_response)
        iterable = iter(instance)
        first = next(iterable)

        # Verify yield count and bytes sent have been updated

        transaction = current_transaction()
        self.assertEqual(transaction._calls_yield, 1)
        self.assertEqual(transaction._bytes_sent, len(first))

        instance.close()

        self.assertEqual(first, b'Hello')
        self.assertTrue(app.close_called)
        self.assertEqual(current_transaction(), None)

    def test_broken_middleware(self):
        """Verify broken middleware does *NOT* close underlying app."""

        app = Application()
        target_app = BrokenMiddleware(app)
        self.assertFalse(app.close_called)

        response = run_app(target_app)
        self.assertFalse(app.close_called)
        self.assertEqual(response, b'Hello World')

    def test_broken_middleware_consume_all_close_transaction(self):
        """ Our middleware will close the transaction when the entire
        response is consumed, even if BrokenMiddleware does not call
        close() on underlying iterable.
        """

        app = Application()
        wrapped_app = WSGIApplicationWrapper(app)
        target_app = BrokenMiddleware(wrapped_app)
        self.assertFalse(app.close_called)

        response = run_app(target_app)
        self.assertTrue(app.close_called)
        self.assertEqual(response, b'Hello World')
        self.assertEqual(current_transaction(), None)

    def test_broken_middleware_consume_some_cannot_close_transaction(self):
        """If entire response isn't consumed *AND* BrokenMiddleware
        doesn't call close() on underlying iterable, then we can't
        close the transaction.
        """

        app = Application()
        wrapped_app = WSGIApplicationWrapper(app)
        target_app = BrokenMiddleware(wrapped_app)
        self.assertFalse(app.close_called)

        environ = {}

        def start_response(status, response_headers):
            pass

        instance = target_app(environ, start_response)
        iterable = iter(instance)
        first = next(iterable)

        # Verify yield count and bytes sent have been updated

        transaction = current_transaction()
        self.assertEqual(transaction._calls_yield, 1)
        self.assertEqual(transaction._bytes_sent, len(first))

        instance.close()

        self.assertEqual(first, b'Hello')
        self.assertFalse(app.close_called)
        self.assertNotEqual(current_transaction(), None)

        # Cleanup: Finish consuming response to close transaction

        list(iterable)
        self.assertTrue(app.close_called)
        self.assertEqual(current_transaction(), None)


if __name__ == '__main__':
    unittest.main()
