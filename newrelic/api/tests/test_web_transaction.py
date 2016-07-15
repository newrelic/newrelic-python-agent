import unittest
import time
import types
import sys
import logging

import newrelic.tests.test_cases

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.web_transaction

import newrelic.agent

is_pypy = '__pypy__' in sys.builtin_module_names

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()

class TestWebTransaction(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_inactive(self):
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_web_transaction(self):
        environ = { "REQUEST_URI": "/web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(transaction.path,
                    'WebTransaction/Uri' + environ["REQUEST_URI"])
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
            self.assertFalse(transaction.background_task)
            time.sleep(1.0)

    def test_script_name_web_transaction(self):
        environ = { "SCRIPT_NAME": "/script_name_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path,
                 'WebTransaction/Uri' + environ["SCRIPT_NAME"])

    def test_path_info_web_transaction(self):
        environ = { "PATH_INFO": "/path_info_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path,
                'WebTransaction/Uri' + environ["PATH_INFO"])

    def test_script_name_path_info_web_transaction(self):
        environ = { "SCRIPT_NAME": "/script_name_",
                    "PATH_INFO": "path_info_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path,
                   "WebTransaction/Uri" + environ["SCRIPT_NAME"] +
                   environ["PATH_INFO"])

    def test_no_path_web_transaction(self):
        environ = {}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path,
                "WebTransaction/Uri/<undefined>")

    def test_named_web_transaction(self):
        environ = { "REQUEST_URI": "DUMMY" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            group = "Function"
            path = "/named_web_transaction"
            transaction.set_transaction_name(path, group)
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
            self.assertEqual(transaction.path,
                    'WebTransaction/'+group+'/'+path)

    def test_background_web_transaction(self):
        environ = { "REQUEST_URI": "DUMMY" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "background_web_transaction"
            transaction.set_transaction_name(path)
            self.assertFalse(transaction.background_task)
            transaction.background_task = True
            self.assertTrue(transaction.background_task)
            transaction.background_task = False
            self.assertFalse(transaction.background_task)
            transaction.background_task = True
            self.assertTrue(transaction.background_task)

    def test_environ_background_web_transaction_bool(self):
        environ = { "REQUEST_URI": "DUMMY",
                    "newrelic.set_background_task": True }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "environ_background_web_transaction_bool"
            transaction.set_transaction_name(path)
            self.assertTrue(transaction.background_task)

    def test_environ_background_web_transaction_string(self):
        environ = { "REQUEST_URI": "DUMMY",
                    "newrelic.set_background_task": "On" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "environ_background_web_transaction_string"
            transaction.set_transaction_name(path)
            self.assertTrue(transaction.background_task)

    def test_exit_on_delete(self):
        if is_pypy:
            return

        environ = { "REQUEST_URI": "/exit_on_delete" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        transaction.__enter__()
        del transaction
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_request_parameters(self):
        environ = { "REQUEST_URI": "/request_parameters",
                    "QUERY_STRING": "a=1&a=2&b=3&c" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            pass

    def test_custom_parameters(self):
        environ = { "REQUEST_URI": "/custom_parameters" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            transaction._custom_params["1"] = "1"
            transaction._custom_params["2"] = "2"
            transaction._custom_params["3"] = 3
            transaction._custom_params["4"] = 4.0
            transaction._custom_params["5"] = ("5", 5)
            transaction._custom_params["6"] = ["6", 6]
            transaction._custom_params["7"] = {"7": 7}
            transaction._custom_params[8] = "8"
            transaction._custom_params[9.0] = "9.0"

    def test_explicit_runtime_error(self):
        environ = { "REQUEST_URI": "/explicit_runtime_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            for i in range(10):
                try:
                    transaction._custom_params["1"] = "1"
                    raise RuntimeError("runtime_error %d" % i)
                except RuntimeError:
                    transaction.record_exception(*sys.exc_info())

    def test_implicit_runtime_error(self):
        environ = { "REQUEST_URI": "/implicit_runtime_error" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/application_disabled" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(), None)
        application.enabled = True

    def test_environ_enabled_bool(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/environ_enabled_bool",
                    "newrelic.enabled": True }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
        application.enabled = True

    def test_environ_disabled_bool(self):
        environ = { "REQUEST_URI": "/environ_disabled_bool",
                    "newrelic.enabled": False }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_environ_enabled_string(self):
        application.enabled = False
        environ = { "REQUEST_URI": "/environ_enabled_string",
                    "newrelic.enabled": "On" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
        application.enabled = True

    def test_environ_disabled_string(self):
        environ = { "REQUEST_URI": "/environ_disabled_string",
                    "newrelic.enabled": "Off" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_ignore_web_transaction(self):
        environ = { "REQUEST_URI": "/ignore_web_transaction" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.ignore_transaction)
            transaction.ignore_transaction = True
            self.assertTrue(transaction.ignore_transaction)
            transaction.ignore_transaction = False
            self.assertFalse(transaction.ignore_transaction)
            transaction.ignore_transaction = True
            self.assertTrue(transaction.ignore_transaction)
            self.assertTrue(transaction.enabled)

    def test_environ_ignore_web_transaction_bool(self):
        environ = { "REQUEST_URI": "/environ_ignore_web_transaction_bool",
                    "newrelic.ignore_transaction": True }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.ignore_transaction)

    def test_environ_ignore_web_transaction_string(self):
        environ = { "REQUEST_URI": "/environ_ignore_web_transaction_string",
                    "newrelic.ignore_transaction": "On" }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.ignore_transaction)

    def test_queue_start(self):
        now = time.time()
        ts = now-0.2

        integer_seconds_tests = [

            # HTTP_X_REQUEST_START seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=%d" % ts},
                ts),

            # HTTP_X_REQUEST_START seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"%d" % ts},
                ts),

            # HTTP_X_QUEUE_START seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"t=%d" % ts},
                ts),

            # HTTP_X_QUEUE_START seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"%d" % ts},
                    ts),

            # mod_wsgi.queue_start seconds
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"%d" % ts},
                    ts),

            # mod_wsgi.queue_start seconds (with t=)
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"t=%d" % ts},
                    ts),

            # All three headers (with t=)
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"t=%d" % (ts
                + 100),"HTTP_X_REQUEST_START":"t=%d" % ts,
                "HTTP_X_QUEUE_START": "t=%d" % (ts + 100)}, ts),

            # All three headers
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"%d" % (ts +
                100),"HTTP_X_REQUEST_START":"%d" % ts,"HTTP_X_QUEUE_START":"%d"
                % (ts + 100)}, ts)

            ]

        float_seconds_tests = [

            # HTTP_X_REQUEST_START seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=%f" % ts},
                ts),

            # HTTP_X_REQUEST_START seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"%f" % ts},
                ts),

            # HTTP_X_QUEUE_START seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"t=%f" % ts},
                ts),

            # HTTP_X_QUEUE_START seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"%f" % ts},
                    ts),

            # mod_wsgi.queue_start seconds
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"%f" % ts},
                    ts),

            # mod_wsgi.queue_start seconds (with t=)
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"t=%f" % ts},
                    ts),

            # All three headers (with t=)
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"t=%f" % (ts
                + 100),"HTTP_X_REQUEST_START":"t=%f" % ts,
                "HTTP_X_QUEUE_START": "t=%f" % (ts + 100)}, ts),

            # All three headers
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"%f" % (ts +
                100),"HTTP_X_REQUEST_START":"%f" % ts,"HTTP_X_QUEUE_START":"%f"
                % (ts + 100)}, ts)

            ]

        integer_milli_seconds_tests = [

            # HTTP_X_REQUEST_START milli-seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=%.0f" % (ts
                * 1000)}, ts),

            # HTTP_X_REQUEST_START milli-seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"%.0f" % (ts *
                1000)}, ts),

            # HTTP_X_QUEUE_START milli-seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"t=%.0f" % (ts *
                1000)}, ts),

            # HTTP_X_QUEUE_START milli-seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"%.0f" % (ts *
                1000)}, ts),

            # mod_wsgi.queue_start milli-seconds (with t=)
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"t=%.0f" % (ts
                * 1000)}, ts),

            # mod_wsgi.queue_start milli-seconds
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"%.0f" % (ts *
                1000)}, ts),

            ]

        integer_micro_seconds_tests = [

            # HTTP_X_REQUEST_START micro-seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=%.0f" % (ts
                * 1000000)}, ts),

            # HTTP_X_REQUEST_START micro-seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"%.0f" % (ts *
                1000000)}, ts),

            # HTTP_X_QUEUE_START micro-seconds (with t=)
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"t=%.0f" % (ts *
                1000000)}, ts),

            # HTTP_X_QUEUE_START micro-seconds
            ({"REQUEST_URI":"/queue_start","HTTP_X_QUEUE_START":"%.0f" % (ts *
                1000000)}, ts),

            # mod_wsgi.queue_start micro-seconds (with t=)
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"t=%.0f" % (ts
                * 1000000)}, ts),

            # mod_wsgi.queue_start micro-seconds
            ({"REQUEST_URI":"/queue_start","mod_wsgi.queue_start":"%.0f" % (ts *
                1000000)}, ts),
                ]

        bad_data_tests = [

            # Empty header.
            {"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":""},

            # Has t= prefix but no time.
            {"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t="},

            # Has non integer for value.
            {"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=X"},

            # Has integer which never satisfies time threshold.
            {"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=1"},

            # Has negative integer.
            {"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=-1"},

            # Time in the future.
            {"REQUEST_URI":"/queue_start","HTTP_X_REQUEST_START":"t=%.0f" % (ts
                + 1000)},

        ]

        for item in integer_seconds_tests:
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, item[0])
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, int(item[1]))

        for item in float_seconds_tests:
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, item[0])
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, item[1], 5)

        # Check for at least 2 significant digits
        for item in integer_milli_seconds_tests:
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, item[0])
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, item[1], 2)

        # Check for at least 6 significant digits
        for item in integer_micro_seconds_tests:
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, item[0])
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, item[1], 5)

        # Check that queue start is always 0.0. Do this check after
        # transaction complete so that will get failure if is None and
        # some arithmetic check is dependent on it always being float.
        for item in bad_data_tests:
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, item)
            with transaction:
                pass
            self.assertEqual(transaction.queue_start, 0.0)

class TestWebsocketWebTransaction(newrelic.tests.test_cases.TestCase):

    def test__is_websocket_websocket_in_environ(self):
        environ = {'HTTP_UPGRADE': 'websocket'}
        self.assertTrue(newrelic.api.web_transaction._is_websocket(
            environ))

    def test__is_websocket_empty_environ(self):
        environ = {}
        self.assertFalse(newrelic.api.web_transaction._is_websocket(
            environ))

    def test__is_websocket_websocket_not_in_environ(self):
        environ = {'HTTP_UPGRADE': 'not a websocket'}
        self.assertFalse(newrelic.api.web_transaction._is_websocket(
            environ))

    def test_web_transaction_disabled(self):
        environ = {
            'HTTP_UPGRADE': 'websocket',
            'REQUEST_URI': '/web_transaction',
        }
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_no_rum_wsgi_application_wrapper(self):
        # Test that the WSGIApplicationWrapper function will not apply RUM
        # middleware if the transaction is a websocket.

        # If this a transaction is a websocket transaction, do not apply RUM
        # middleware.  This is due to a bug in gevent-websocket (0.9.5)
        # package. If our _WSGIApplicationMiddleware is applied a websocket
        # connection cannot be made. The gevent-websocket package incorrectly
        # handles applications that return generators (which the middleware is
        # a type of), therefore middleware application is avoided. It doesn't
        # make sense for websockets to include RUM anyway.

        def wrapped(environ, start_response):
            return True

        def start_response(status, headers):
            return 'write'

        environ = {
            'HTTP_UPGRADE': 'websocket',
            'REQUEST_URI': '/web_transaction',
        }

        wrapped_wsgi_app = newrelic.api.web_transaction.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the value of wrapped(*args, **kwargs).
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        self.assertEqual(func_wrapper.generator,
                wrapped(environ, start_response))

    def test_use_rum_when_not_websocket(self):
        if is_pypy:
            return

        # Test that the WSGIApplicationWrapper function will apply RUM
        # middleware if the transaction is not a websocket.
        def wrapped(environ, start_response):
            return True

        def start_response(status, headers):
            return 'write'

        environ = {'REQUEST_URI': '/web_transaction'}

        wrapped_wsgi_app = newrelic.api.web_transaction.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        self.assertEqual(type(func_wrapper.generator), types.GeneratorType)

    def test_no_rum_when_not_websocket_and_autorum_disabled_is_True(self):
        if is_pypy:
            return

        # If autorum_disabled = True but the transaction is not a websocket,
        # RUM should not be applied.

        def wrapped(environ, start_response):
            return True

        def start_response(status, headers):
            return 'write'

        environ = {
            'REQUEST_URI': '/web_transaction',
            'newrelic.disable_browser_autorum': True,
        }

        wrapped_wsgi_app = newrelic.api.web_transaction.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        self.assertEqual(func_wrapper.generator,
                wrapped(environ, start_response))

    def test_no_rum_is_websocket_autorum_disabled(self):
        # If autorum_disabled = True and the transaction is a websocket, RUM
        # should not be applied.
        def wrapped(environ, start_response):
            return True

        def start_response(status, headers):
            return 'write'

        environ = {
            'HTTP_UPGRADE': 'websocket',
            'REQUEST_URI': '/web_transaction',
            'newrelic.disable_browser_autorum': True,
        }

        wrapped_wsgi_app = newrelic.api.web_transaction.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        self.assertEqual(func_wrapper.generator,
                wrapped(environ, start_response))

if __name__ == '__main__':
    unittest.main()
