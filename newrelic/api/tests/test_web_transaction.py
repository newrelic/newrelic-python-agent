import pytest
import sys
import time
import unittest

import newrelic.api.settings
import newrelic.api.application
import newrelic.api.transaction
import newrelic.api.wsgi_application as wsgi_application
import newrelic.api.web_transaction
import newrelic.tests.test_cases
from newrelic.common.encoding_utils import json_encode, obfuscate
from newrelic.tests.test_cases import connect # noqa


is_pypy = '__pypy__' in sys.builtin_module_names

settings = newrelic.api.settings.settings()
application = newrelic.api.application.application_instance()


class TestWebTransaction(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_inactive(self):
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_web_transaction(self):
        environ = {"REQUEST_URI": "/web_transaction"}
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
        environ = {"SCRIPT_NAME": "/script_name_web_transaction"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path,
                 'WebTransaction/Uri' + environ["SCRIPT_NAME"])

    def test_path_info_web_transaction(self):
        environ = {"PATH_INFO": "/path_info_web_transaction"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertEqual(transaction.path,
                'WebTransaction/Uri' + environ["PATH_INFO"])

    def test_script_name_path_info_web_transaction(self):
        environ = {"SCRIPT_NAME": "/script_name_",
                "PATH_INFO": "path_info_web_transaction"}
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
        environ = {"REQUEST_URI": "DUMMY"}
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
                             'WebTransaction/' + group + '/' + path)

    def test_background_web_transaction(self):
        environ = {"REQUEST_URI": "DUMMY"}
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
        environ = {"REQUEST_URI": "DUMMY",
                "newrelic.set_background_task": True}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "environ_background_web_transaction_bool"
            transaction.set_transaction_name(path)
            self.assertTrue(transaction.background_task)

    def test_environ_background_web_transaction_string(self):
        environ = {"REQUEST_URI": "DUMMY",
                "newrelic.set_background_task": "On"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            path = "environ_background_web_transaction_string"
            transaction.set_transaction_name(path)
            self.assertTrue(transaction.background_task)

    def test_exit_on_delete(self):
        if is_pypy:
            return

        environ = {"REQUEST_URI": "/exit_on_delete"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        transaction.__enter__()
        del transaction
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_request_parameters(self):
        environ = {"REQUEST_URI": "/request_parameters",
                "QUERY_STRING": "a=1&a=2&b=3&c"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            pass

    def test_custom_parameters(self):
        environ = {"REQUEST_URI": "/custom_parameters"}
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
        environ = {"REQUEST_URI": "/explicit_runtime_error"}
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
        environ = {"REQUEST_URI": "/implicit_runtime_error"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        application.enabled = False
        environ = {"REQUEST_URI": "/application_disabled"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    None)
        application.enabled = True

    def test_environ_enabled_bool(self):
        application.enabled = False
        environ = {"REQUEST_URI": "/environ_enabled_bool",
                "newrelic.enabled": True}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
        application.enabled = True

    def test_environ_disabled_bool(self):
        environ = {"REQUEST_URI": "/environ_disabled_bool",
                "newrelic.enabled": False}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    None)

    def test_environ_enabled_string(self):
        application.enabled = False
        environ = {"REQUEST_URI": "/environ_enabled_string",
                "newrelic.enabled": "On"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
        application.enabled = True

    def test_environ_disabled_string(self):
        environ = {"REQUEST_URI": "/environ_disabled_string",
                "newrelic.enabled": "Off"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    None)

    def test_ignore_web_transaction(self):
        environ = {"REQUEST_URI": "/ignore_web_transaction"}
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
        environ = {"REQUEST_URI": "/environ_ignore_web_transaction_bool",
                "newrelic.ignore_transaction": True}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.ignore_transaction)

    def test_environ_ignore_web_transaction_string(self):
        environ = {"REQUEST_URI": "/environ_ignore_web_transaction_string",
                "newrelic.ignore_transaction": "On"}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertTrue(transaction.ignore_transaction)

    def test_no_rum_insertion_sync_application_call(self):
        # The application wrapper should always directly call application
        # regardless of rum settings

        called = [False]

        def wrapped(environ, start_response):
            called[0] = True
            return ['response']

        def start_response(status, headers):
            return 'write'

        environ = {'REQUEST_URI': '/web_transaction',
                'newrelic.disable_browser_autorum': True}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)

        try:
            self.assertTrue(called[0])
        finally:
            func_wrapper.close()

    def test_process_response_status_int(self):
        environ = {'REQUEST_URI': '/environ_process_response_status'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        status = 200
        response_headers = {}
        transaction.process_response(status, response_headers)

        assert transaction.response_code == 0

    def test_process_response_status_str(self):
        environ = {'REQUEST_URI': '/environ_process_response_status_str'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        status = '410'
        response_headers = {}
        transaction.process_response(status, response_headers)

        assert transaction.response_code == 410

    def test_process_response_status_str_msg(self):
        environ = {'REQUEST_URI': '/environ_process_response_status_str_msg'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        status = '200 OK'
        response_headers = {}
        transaction.process_response(status, response_headers)

        assert transaction.response_code == 200

    def test_sync_application_call(self):
        # The application wrapper should always directly call application
        # regardless of rum settings

        called = [False]

        def wrapped(environ, start_response):
            called[0] = True
            return True

        def start_response(status, headers):
            return 'write'

        environ = {'REQUEST_URI': '/web_transaction',
                'newrelic.disable_browser_autorum': False}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)

        try:
            self.assertTrue(called[0])
        finally:
            func_wrapper.close()

    def test_app_names_in_environ(self):
        def wrapped(environ, start_response):
            start_response('200 OK', [])
            return [b'HAI']

        def start_response(status, headers):
            return 'write'

        environ = {'REQUEST_URI': '/app_names_in_environ',
                'newrelic.app_name': 'webapp_test_a;webapp_test_b'}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        it = wrapped_wsgi_app(environ, start_response)
        tx = newrelic.api.transaction.current_transaction()
        try:
            assert tx.application.name == 'webapp_test_a'
            assert tx.application.linked_applications[0] == 'webapp_test_b'
        finally:
            it.close()

    def test_queue_start(self):
        now = time.time()
        ts = now - 0.2

        integer_seconds_tests = [

            # HTTP_X_REQUEST_START seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "t=%d" % ts}, ts),

            # HTTP_X_REQUEST_START seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "%d" % ts}, ts),

            # HTTP_X_QUEUE_START seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "t=%d" % ts}, ts),

            # HTTP_X_QUEUE_START seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "%d" % ts}, ts),

            # mod_wsgi.queue_start seconds
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "%d" % ts}, ts),

            # mod_wsgi.queue_start seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "t=%d" % ts}, ts),

            # All three headers (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "t=%d" % (ts + 100),
                    "HTTP_X_REQUEST_START": "t=%d" % ts,
                    "HTTP_X_QUEUE_START": "t=%d" % (ts + 100)}, ts),

            # All three headers
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "%d" % (ts + 100),
                    "HTTP_X_REQUEST_START": "%d" % ts,
                    "HTTP_X_QUEUE_START": "%d" % (ts + 100)}, ts)
        ]

        float_seconds_tests = [

            # HTTP_X_REQUEST_START seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "t=%f" % ts}, ts),

            # HTTP_X_REQUEST_START seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "%f" % ts}, ts),

            # HTTP_X_QUEUE_START seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "t=%f" % ts}, ts),

            # HTTP_X_QUEUE_START seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "%f" % ts}, ts),

            # mod_wsgi.queue_start seconds
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "%f" % ts}, ts),

            # mod_wsgi.queue_start seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "t=%f" % ts}, ts),

            # All three headers (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "t=%f" % (ts + 100),
                    "HTTP_X_REQUEST_START": "t=%f" % ts,
                    "HTTP_X_QUEUE_START": "t=%f" % (ts + 100)}, ts),

            # All three headers
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "%f" % (ts + 100),
                    "HTTP_X_REQUEST_START": "%f" % ts,
                    "HTTP_X_QUEUE_START": "%f" % (ts + 100)}, ts)

        ]

        integer_milli_seconds_tests = [

            # HTTP_X_REQUEST_START milli-seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "t=%.0f" % (ts * 1000)}, ts),

            # HTTP_X_REQUEST_START milli-seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "%.0f" % (ts * 1000)}, ts),

            # HTTP_X_QUEUE_START milli-seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "t=%.0f" % (ts * 1000)}, ts),

            # HTTP_X_QUEUE_START milli-seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "%.0f" % (ts * 1000)}, ts),

            # mod_wsgi.queue_start milli-seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "t=%.0f" % (ts * 1000)}, ts),

            # mod_wsgi.queue_start milli-seconds
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "%.0f" % (ts * 1000)}, ts),

        ]

        integer_micro_seconds_tests = [

            # HTTP_X_REQUEST_START micro-seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "t=%.0f" % (ts * 1000000)}, ts),

            # HTTP_X_REQUEST_START micro-seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "%.0f" % (ts * 1000000)}, ts),

            # HTTP_X_QUEUE_START micro-seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "t=%.0f" % (ts * 1000000)}, ts),

            # HTTP_X_QUEUE_START micro-seconds
            ({"REQUEST_URI": "/queue_start",
                    "HTTP_X_QUEUE_START": "%.0f" % (ts * 1000000)}, ts),

            # mod_wsgi.queue_start micro-seconds (with t=)
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "t=%.0f" % (ts * 1000000)}, ts),

            # mod_wsgi.queue_start micro-seconds
            ({"REQUEST_URI": "/queue_start",
                    "mod_wsgi.queue_start": "%.0f" % (ts * 1000000)}, ts),

    ]

        bad_data_tests = [

            # Empty header.
            {"REQUEST_URI": "/queue_start", "HTTP_X_REQUEST_START": ""},

            # Has t= prefix but no time.
            {"REQUEST_URI": "/queue_start", "HTTP_X_REQUEST_START": "t="},

            # Has non integer for value.
            {"REQUEST_URI": "/queue_start", "HTTP_X_REQUEST_START": "t=X"},

            # Has integer which never satisfies time threshold.
            {"REQUEST_URI": "/queue_start", "HTTP_X_REQUEST_START": "t=1"},

            # Has negative integer.
            {"REQUEST_URI": "/queue_start", "HTTP_X_REQUEST_START": "t=-1"},

            # Time in the future.
            {"REQUEST_URI": "/queue_start",
                    "HTTP_X_REQUEST_START": "t=%.0f" % (ts + 1000)},

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

    def test_accept_payload_no_newrelic_header(self):
        try:
            original_setting = application.settings.distributed_tracing.enabled
            application.settings.distributed_tracing.enabled = True

            environ = {"REQUEST_URI": "/web_transaction"}
            transaction = newrelic.api.web_transaction.WebTransaction(
                    application, environ)

            with transaction:
                assert ('Supportability/DistributedTrace/'
                        'AcceptPayload/Ignored/Null'
                        not in transaction._transaction_metrics)
        finally:
            application.settings.distributed_tracing.enabled = original_setting


class TestGenericWebTransaction(newrelic.tests.test_cases.TestCase):

    requires_collector = True

    def test_inactive(self):
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_web_transaction(self):
        request_path = '/web_transaction'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                request_path=request_path)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(transaction.path,
                    'WebTransaction/Uri' + request_path)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
            self.assertFalse(transaction.background_task)

    def test_web_transaction_named(self):
        transaction_name = 'sample'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                transaction_name)

        with transaction:
            self.assertEqual(transaction.name, transaction_name)

    def test_web_transaction_scheme(self):
        scheme = 'dummy_scheme'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                scheme=scheme)

        with transaction:
            self.assertEqual(transaction._request_scheme, scheme)

    def test_web_transaction_host(self):
        host = 'dummy_host'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                host=host)

        with transaction:
            self.assertEqual(transaction._request_host, host)

    def test_web_transaction_port(self):
        port = 8080
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                port=port)

        with transaction:
            self.assertEqual(transaction._port, port)

    def test_web_transaction_request_method(self):
        request_method = 'GET'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                request_method=request_method)

        with transaction:
            self.assertEqual(transaction._request_method, request_method)

    def test_web_transaction_headers(self):
        headers = {'DUMMY': 'value'}
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                headers=headers.items())

        with transaction:
            self.assertEqual(transaction._request_headers['dummy'], 'value')

    def test_web_transaction_headers_bytes(self):
        headers = {b'DUMMY': b'value'}
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                headers=headers.items())

        with transaction:
            self.assertEqual(transaction._request_headers['dummy'], b'value')

    def test_no_path_web_transaction(self):
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None)
        with transaction:
            self.assertEqual(transaction.path,
                "WebTransaction/Uri/<undefined>")

    def test_named_web_transaction(self):
        request_path = 'DUMMY'
        name = 'named_web_transaction'
        group = 'Function'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                name,
                group=group,
                request_path=request_path)
        with transaction:
            self.assertTrue(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    transaction)
            self.assertEqual(transaction.path,
                             'WebTransaction/' + group + '/' + name)

    def test_exit_on_delete(self):
        if is_pypy:
            return

        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None)
        transaction.__enter__()
        del transaction
        self.assertEqual(newrelic.api.transaction.current_transaction(), None)

    def test_query_string(self):
        query_string = "a=1&a=2&b=3"
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                query_string=query_string)
        with transaction:
            self.assertEqual(transaction._request_params['a'], ['1', '2'])
            self.assertEqual(transaction._request_params['b'], ['3'])

    def test_query_string_bytes(self):
        query_string = b'a=1&a=2&b=3'
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                query_string=query_string)
        with transaction:
            self.assertEqual(transaction._request_params['a'], ['1', '2'])
            self.assertEqual(transaction._request_params['b'], ['3'])

    def test_query_string_cp424(self):
        query_string = 'a=1&a=2&b=3'.encode('cp424')
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                query_string=query_string)
        with transaction:
            assert not transaction._request_params

    def test_capture_params_high_security(self):
        original = application.settings.high_security
        application.settings.high_security = True

        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None)

        try:
            with transaction:
                assert not transaction.capture_params
        finally:
            application.settings.high_security = original

    def test_process_synthetics_empty_header(self):
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None)

        with transaction:
            assert transaction.synthetics_header is None
            assert transaction.synthetics_resource_id is None
            assert transaction.synthetics_job_id is None
            assert transaction.synthetics_monitor_id is None

    def test_process_synthetics_valid_header(self):
        payload = [1, 1, 'resource', 'job', 'monitor']
        synthetics_header = obfuscate(json_encode(payload),
                application.settings.encoding_key)

        headers = {'X-NewRelic-Synthetics': synthetics_header}

        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                headers=headers.items())

        with transaction:
            self.assertEqual(transaction.synthetics_header, synthetics_header)
            self.assertEqual(transaction.synthetics_resource_id, 'resource')
            self.assertEqual(transaction.synthetics_job_id, 'job')
            self.assertEqual(transaction.synthetics_monitor_id, 'monitor')

    def test_process_synthetics_version2_header(self):
        payload = [2, 1, 'resource', 'job', 'monitor']
        synthetics_header = obfuscate(json_encode(payload),
                application.settings.encoding_key)

        headers = {'X-NewRelic-Synthetics': synthetics_header}

        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                headers=headers.items())

        with transaction:
            assert transaction.synthetics_header is None
            assert transaction.synthetics_resource_id is None
            assert transaction.synthetics_job_id is None
            assert transaction.synthetics_monitor_id is None

    def test_process_synthetics_untrusted_accountid_header(self):
        payload = [1, 9999, 'resource', 'job', 'monitor']
        synthetics_header = obfuscate(json_encode(payload),
                application.settings.encoding_key)

        headers = {'X-NewRelic-Synthetics': synthetics_header}

        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                headers=headers.items())

        with transaction:
            assert transaction.synthetics_header is None
            assert transaction.synthetics_resource_id is None
            assert transaction.synthetics_job_id is None
            assert transaction.synthetics_monitor_id is None

    def test_process_synthetics_malformed_header(self):
        payload = ['version', 1, 'resource', 'job', 'monitor']
        synthetics_header = obfuscate(json_encode(payload),
                application.settings.encoding_key)

        headers = {'X-NewRelic-Synthetics': synthetics_header}

        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None,
                headers=headers.items())

        with transaction:
            assert transaction.synthetics_header is None
            assert transaction.synthetics_resource_id is None
            assert transaction.synthetics_job_id is None
            assert transaction.synthetics_monitor_id is None

    def test_implicit_runtime_error(self):
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None)
        try:
            with transaction:
                raise RuntimeError("runtime_error")
        except RuntimeError:
            pass

    def test_application_disabled(self):
        original = application.enabled
        application.enabled = False
        transaction = newrelic.api.web_transaction.GenericWebTransaction(
                application,
                None)

        try:
            with transaction:
                self.assertFalse(transaction.enabled)
                self.assertEqual(
                        newrelic.api.transaction.current_transaction(),
                        None)
        finally:
            application.enabled = original

    def test_queue_headers_integer(self):
        now = time.time()
        ts = int(now - 5)

        integer_seconds_tests = [
            # X-Request-Start seconds (with t=)
            ({"X-Request-Start": "t=%d" % ts}, ts),

            # X-Request-Start seconds
            ({"X-Request-Start": "%d" % ts}, ts),

            # X-Queue-Start seconds (with t=)
            ({"X-Queue-Start": "t=%d" % ts}, ts),

            # X-Queue-Start seconds (with t=) bytes
            ({b"X-Queue-Start": ("t=%d" % ts).encode('utf-8')}, ts),

            # X-Queue-Start seconds
            ({"X-Queue-Start": "%d" % ts}, ts),

            # Both headers (with t=)
            ({"X-Request-Start": "t=%d" % ts,
              "X-Queue-Start": "t=%d" % (ts + 100)}, ts),

            # Both headers
            ({"X-Request-Start": "%d" % ts,
              "X-Queue-Start": "%d" % (ts + 100)}, ts)
        ]

        for headers, queue_start in integer_seconds_tests:
            transaction = newrelic.api.web_transaction.GenericWebTransaction(
                    application,
                    'queue_start',
                    headers=headers.items())
            with transaction:
                self.assertEqual(transaction.queue_start, queue_start)

    def test_queue_headers_seconds(self):
        ts = time.time() - 0.2

        float_seconds_tests = [
            # X-Request-Start seconds (with t=)
            ({"X-Request-Start": "t=%f" % ts}, ts),

            # X-Request-Start seconds (with t=) bytes
            ({b"X-Request-Start": ("t=%f" % ts).encode('utf-8')}, ts),

            # X-Request-Start seconds
            ({"X-Request-Start": "%f" % ts}, ts),

            # X-Queue-Start seconds (with t=)
            ({"X-Queue-Start": "t=%f" % ts}, ts),

            # X-Queue-Start seconds (with t=) bytes
            ({b"X-Queue-Start": ("t=%f" % ts).encode('utf-8')}, ts),

            # X-Queue-Start seconds
            ({"X-Queue-Start": "%f" % ts}, ts),

            # Both headers (with t=)
            ({"X-Request-Start": "t=%f" % ts,
              "X-Queue-Start": "t=%f" % (ts + 100)}, ts),

            # Both headers
            ({"X-Request-Start": "%f" % ts,
              "X-Queue-Start": "%f" % (ts + 100)}, ts)
        ]

        for headers, queue_start in float_seconds_tests:
            transaction = newrelic.api.web_transaction.GenericWebTransaction(
                    application,
                    'queue_start',
                    headers=headers.items())
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, queue_start, 5)

    def test_queue_headers_milli(self):
        ts = time.time() - 0.2

        integer_milli_seconds_tests = [
            # X-Request-Start milli-seconds (with t=)
            ({"X-Request-Start": "t=%.0f" % (ts * 1000)}, ts),

            # X-Request-Start milli-seconds
            ({"X-Request-Start": "%.0f" % (ts * 1000)}, ts),

            # X-Queue-Start milli-seconds (with t=)
            ({"X-Queue-Start": "t=%.0f" % (ts * 1000)}, ts),

            # X-Queue-Start milli-seconds
            ({"X-Queue-Start": "%.0f" % (ts * 1000)}, ts),
        ]

        # Check for at least 2 significant digits
        for headers, queue_start in integer_milli_seconds_tests:
            transaction = newrelic.api.web_transaction.GenericWebTransaction(
                    application,
                    'queue_start',
                    headers=headers.items())
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, queue_start, 2)

    def test_queue_headers_micro(self):
        ts = time.time() - 0.2

        integer_micro_seconds_tests = [
            # X-Request-Start micro-seconds (with t=)
            ({"X-Request-Start": "t=%.0f" % (ts * 1000000)}, ts),

            # X-Request-Start micro-seconds
            ({"X-Request-Start": "%.0f" % (ts * 1000000)}, ts),

            # X-Queue-Start micro-seconds (with t=)
            ({"X-Queue-Start": "t=%.0f" % (ts * 1000000)}, ts),

            # X-Queue-Start micro-seconds
            ({"X-Queue-Start": "%.0f" % (ts * 1000000)}, ts),
        ]

        # Check for at least 6 significant digits
        for headers, queue_start in integer_micro_seconds_tests:
            transaction = newrelic.api.web_transaction.GenericWebTransaction(
                    application,
                    'queue_start',
                    headers=headers.items())
            with transaction:
                self.assertAlmostEqual(transaction.queue_start, queue_start, 5)

    def test_queue_headers_bad(self):
        bad_data_tests = [
            # Empty header.
            {"X-Request-Start": ""},

            # Has t= prefix but no time.
            {"X-Request-Start": "t="},

            # Has non integer for value.
            {"X-Request-Start": "t=X"},

            # Has integer which never satisfies time threshold.
            {"X-Request-Start": "t=1"},

            # Has negative integer.
            {"X-Request-Start": "t=-1"},

            # Time in the future.
            {"X-Request-Start": "t=%.0f" % (time.time() + 1000)},
        ]

        # Check that queue start always defaults to 0.0. Do this check after
        # transaction complete so that the test will fail if is queue start is
        # None and some arithmetic check is dependent on it always being float.
        for headers in bad_data_tests:
            transaction = newrelic.api.web_transaction.GenericWebTransaction(
                    application,
                    'queue_start',
                    headers=headers.items())
            with transaction:
                pass
            self.assertEqual(transaction.queue_start, 0.0)


class TestWebsocketWebTransaction(newrelic.tests.test_cases.TestCase):

    def test__is_websocket_websocket_in_environ(self):
        environ = {'HTTP_UPGRADE': 'websocket'}
        self.assertTrue(newrelic.api.web_transaction._is_websocket(environ))

    def test__is_websocket_empty_environ(self):
        environ = {}
        self.assertFalse(newrelic.api.web_transaction._is_websocket(environ))

    def test__is_websocket_websocket_not_in_environ(self):
        environ = {'HTTP_UPGRADE': 'not a websocket'}
        self.assertFalse(newrelic.api.web_transaction._is_websocket(environ))

    def test_web_transaction_disabled(self):
        environ = {'HTTP_UPGRADE': 'websocket',
                'REQUEST_URI': '/web_transaction'}
        transaction = newrelic.api.web_transaction.WebTransaction(
                application, environ)
        with transaction:
            self.assertFalse(transaction.enabled)
            self.assertEqual(newrelic.api.transaction.current_transaction(),
                    None)

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
            return ['response']

        def start_response(status, headers):
            return 'write'

        environ = {'HTTP_UPGRADE': 'websocket',
                'REQUEST_URI': '/web_transaction'}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the value of wrapped(*args, **kwargs).
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        try:
            self.assertEqual(func_wrapper.generator,
                    wrapped(environ, start_response))
        finally:
            func_wrapper.close()

    def test_use_rum_when_not_websocket(self):
        # Test that the WSGIApplicationWrapper function will apply RUM
        # middleware if the transaction is not a websocket.
        def wrapped(environ, start_response):
            return ['response']

        def start_response(status, headers):
            return 'write'

        environ = {'REQUEST_URI': '/web_transaction'}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        try:
            self.assertNotEqual(func_wrapper.generator,
                    wrapped(environ, start_response))
        finally:
            func_wrapper.close()

    def test_no_rum_when_not_websocket_and_autorum_disabled_is_True(self):
        # If autorum_disabled = True but the transaction is not a websocket,
        # RUM should not be applied.

        def wrapped(environ, start_response):
            return ['response']

        def start_response(status, headers):
            return 'write'

        environ = {'REQUEST_URI': '/web_transaction',
                'newrelic.disable_browser_autorum': True}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        try:
            self.assertEqual(func_wrapper.generator,
                    wrapped(environ, start_response))
        finally:
            func_wrapper.close()

    def test_no_rum_is_websocket_autorum_disabled(self):
        # If autorum_disabled = True and the transaction is a websocket, RUM
        # should not be applied.
        def wrapped(environ, start_response):
            return ['response']

        def start_response(status, headers):
            return 'write'

        environ = {'HTTP_UPGRADE': 'websocket',
                'REQUEST_URI': '/web_transaction',
                'newrelic.disable_browser_autorum': True}

        wrapped_wsgi_app = wsgi_application.WSGIApplicationWrapper(
                wrapped, application=application)

        # Call the now wrapped application. It will return a
        # _WSGIApplicationIterable object. The generator attribute on this
        # object is the middleware instance.
        func_wrapper = wrapped_wsgi_app(environ, start_response)
        try:
            self.assertEqual(func_wrapper.generator,
                    wrapped(environ, start_response))
        finally:
            func_wrapper.close()


@pytest.mark.parametrize('capture_params', [  # NOQA
        None,
        False,
        True,
])
def test_http_referer_header_stripped_transaction(capture_params, connect):
    # Make sure that 'HTTP_REFERER' header params are stripped, regardless of
    # 'capture_params' config.
    url = "http://www.wruff.org"
    params = "?token=meow"
    environ = {"HTTP_REFERER": url + params, "REQUEST_URI": "DUMMY",
            "newrelic.enabled": "true"}

    if capture_params is not None:
        environ["newrelic.capture_request_params"] = capture_params

    assert application.settings
    transaction = newrelic.api.web_transaction.WebTransaction(
            application, environ)
    assert transaction._request_environment["HTTP_REFERER"] == url
    assert transaction.capture_params == capture_params


@pytest.mark.parametrize('multiplier', (
    0.0, 1.0, 1000.0, 1000000.0, 2.0
))
def test_parse_time_stamp(monkeypatch, multiplier):
    # Set the time to be Jan 2 2000 since times earlier than Jan 1 2000 are
    # rejected.
    JAN_2_2000 = time.mktime((2000, 1, 2, 0, 0, 0, 0, 0, 0))
    monkeypatch.setattr(time, 'time', lambda: JAN_2_2000)

    timestamp_s = JAN_2_2000 - 60

    expected = timestamp_s
    if multiplier < 1 or multiplier == 2.0:
        expected = 0.0

    _parse_time_stamp = newrelic.api.web_transaction._parse_time_stamp
    assert _parse_time_stamp(timestamp_s * multiplier) == expected


if __name__ == '__main__':
    unittest.main()
