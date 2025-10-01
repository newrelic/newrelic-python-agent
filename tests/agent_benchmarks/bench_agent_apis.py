# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from testing_support.asgi_testing import AsgiTest
from testing_support.sample_asgi_applications import simple_app_v3_raw

from newrelic.agent import (
    add_custom_attribute,
    add_custom_attributes,
    add_custom_span_attribute,
    add_framework_info,
    application,
    application_settings,
    asgi_application,
    background_task,
    callable_name,
    capture_request_params,
    current_span_id,
    current_trace,
    current_trace_id,
    current_transaction,
    database_trace,
    datastore_trace,
    disable_browser_autorum,
    end_of_transaction,
    error_trace,
    external_trace,
    extra_settings,
    function_trace,
    function_wrapper,
    generator_trace,
    get_browser_timing_header,
    get_linking_metadata,
    global_settings,
    ignore_transaction,
    in_function,
    initialize,
    insert_html_snippet,
    message_trace,
    message_transaction,
    notice_error,
    out_function,
    post_function,
    pre_function,
    profile_trace,
    record_custom_event,
    record_custom_metric,
    record_custom_metrics,
    set_background_task,
    set_error_group_callback,
    set_llm_token_count_callback,
    set_transaction_name,
    set_user_id,
    suppress_apdex_metric,
    suppress_transaction_trace,
    transaction_name,
    verify_body_exists,
    web_transaction,
    wsgi_application,
)
from newrelic.api.transaction import record_dimensional_metric

from . import benchmark


@benchmark
class TraceDecorators:
    @background_task()
    def bench_database_trace(self):
        @database_trace(sql="SELECT * FROM users WHERE id = 1")
        def test():
            pass

        test()

    @background_task()
    def bench_datastore_trace(self):
        @datastore_trace(
            product="test_product",
            target="test_target",
            operation="test_operation",
            host="test_host",
            port_path_or_id="test_port",
            database_name="test_db",
        )
        def test():
            pass

        test()

    @background_task()
    def bench_profile_trace(self):
        @profile_trace()
        def test():
            pass

        test()

    @background_task()
    def bench_message_trace(self):
        @message_trace(
            library="test_library",
            operation="test_operation",
            destination_type="test_destination_type",
            destination_name="test_destination_name",
        )
        def test():
            pass

        test()

    @background_task()
    def bench_external_trace(self):
        @external_trace(library="test_library", url="http://example.org", method="GET")
        def test():
            pass

        test()

    @background_task()
    def bench_function_trace(self):
        @function_trace(name="TestFunction", group="TestGroup", params={"param1": "value1"})
        def test():
            pass

        test()

    @background_task()
    def bench_generator_trace(self):
        @generator_trace(name="TestGenerator", group="TestGroup")
        def test():
            for i in range(3):  # noqa: UP028
                yield i

        list(test())  # Consume the generator

    @background_task()
    def bench_error_trace(self):
        @error_trace()
        def test():
            raise ValueError("Test error")

        try:
            test()
        except ValueError:
            pass


@benchmark
class TransactionDecorators:
    @background_task(name="TestBackgroundTask", group="TestGroup")
    def bench_background_task(self):
        pass

    @web_transaction(
        name="TestWebTransaction",
        group="TestGroup",
        scheme="https",
        host="example.org",
        port=443,
        request_method="GET",
        request_path="/test",
        query_string="foo=bar&boo=baz",
        headers={"MyHeader": "MyValue"},
    )
    def bench_web_transaction(self):
        pass

    def bench_wsgi_application(self):
        @wsgi_application(framework=("my_framework", (1, 2, 3)), dispatcher=("my_dispatcher", (4, 5, 6)))
        def test(environ, start_response):
            status = "200 OK"
            headers = [("Content-Type", "text/plain")]
            start_response(status, headers)
            return [b"Hello, World!"]

        # Simulate a WSGI request
        list(test({}, lambda status, headers: None))

    def bench_asgi_application(self):
        decorator = asgi_application(framework=("my_framework", (1, 2, 3)), dispatcher=("my_dispatcher", (4, 5, 6)))
        simple_app_v3 = decorator(simple_app_v3_raw)
        # Test the app with AsgiTest
        AsgiTest(simple_app_v3).get("/")

    def bench_message_transaction(self):
        @message_transaction(
            library="test_library",
            destination_type="test_destination_type",
            destination_name="test_destination_name",
            routing_key="test_routing_key",
            exchange_type="test_exchange_type",
            headers={"MyHeader": "MyValue"},
            queue_name="test_queue_name",
            reply_to="test_reply_to",
            correlation_id="test_correlation_id",
        )
        def test():
            pass

        test()


@benchmark
class MetricApis:
    TEST_TIMESLICE_METRIC = {"count": 1, "total": 1, "min": 1, "max": 1, "sum_of_squares": 1}
    TEST_COUNT_METRIC = {"count": 1}

    @background_task()
    def bench_record_custom_metric(self):
        record_custom_metric("TestMetric", 1)

    @background_task()
    def bench_record_custom_metric_count(self):
        record_custom_metric("TestCountMetric", self.TEST_COUNT_METRIC)

    @background_task()
    def bench_record_custom_metric_timeslice(self):
        record_custom_metric("TestTimesliceMetric", self.TEST_TIMESLICE_METRIC)

    @background_task()
    def bench_record_custom_metrics(self):
        record_custom_metrics(
            [
                ("TestTimesliceMetric", self.TEST_TIMESLICE_METRIC),
                ("TestCountMetric", self.TEST_COUNT_METRIC),
                ("TestMetric", 1),
            ]
        )

    @background_task()
    def bench_record_dimensional_metric(self):
        record_dimensional_metric("TestDimensionalMetric", 1, tags={"tag": "tag"})


@benchmark
class EventApis:
    @background_task()
    def bench_notice_error(self):
        try:
            raise ValueError("Test error")
        except ValueError:
            notice_error()

    @background_task()
    def bench_record_custom_event(self):
        record_custom_event("TestEvent", {"attribute1": "value1", "attribute2": 2})

    @background_task()
    def bench_record_exception(self):
        pass

    @background_task()
    def bench_record_llm_feedback_event(self):
        pass

    @background_task()
    def bench_record_log_event(self):
        pass

    @background_task()
    def bench_record_ml_event(self):
        pass


@benchmark
class FunctionWrapperApis:
    def _test_function(self):
        pass

    def bench_callable_name(self):
        callable_name(self._test_function)

    def bench_function_wrapper(self):
        @function_wrapper
        def wrapper(wrapped, instance, args, kwargs):
            return wrapped(*args, **kwargs)

        wrapped_function = wrapper(self._test_function)
        wrapped_function()

    def bench_in_function(self):
        @in_function
        def wrapper(self, *args, **kwargs):
            return ((self, *args), kwargs)

        wrapped_function = wrapper(self._test_function)
        wrapped_function()

    def bench_out_function(self):
        @out_function
        def wrapper(result):
            return result

        wrapped_function = wrapper(self._test_function)
        wrapped_function()

    def bench_pre_function(self):
        @pre_function
        def wrapper(self, *args, **kwargs):
            return

        wrapped_function = wrapper(self._test_function)
        wrapped_function()

    def bench_post_function(self):
        @post_function
        def wrapper(self, *args, **kwargs):
            return

        wrapped_function = wrapper(self._test_function)
        wrapped_function()


@benchmark
class TransactionApis:
    @background_task()
    def bench_current_transaction(self):
        current_transaction()

    @background_task()
    def bench_ignore_transaction(self):
        ignore_transaction()

    @background_task()
    def bench_end_of_transaction(self):
        end_of_transaction()

    @background_task()
    def bench_disable_browser_autorum(self):
        disable_browser_autorum()

    @web_transaction()
    def bench_set_background_task(self):
        set_background_task()

    @background_task()
    def bench_set_user_id(self):
        set_user_id("test_user_id")

    @background_task()
    def bench_set_transaction_name(self):
        set_transaction_name("test_transaction_name")

    @background_task()
    def bench_set_llm_token_count_callback(self):
        set_llm_token_count_callback(lambda *args, **kwargs: 1)

    @background_task()
    def bench_set_error_group_callback(self):
        set_error_group_callback(lambda *args, **kwargs: "test_error_group")

    @background_task()
    def bench_suppress_apdex_metric(self):
        suppress_apdex_metric()

    @background_task()
    def bench_suppress_transaction_trace(self):
        suppress_transaction_trace()

    @background_task()
    def bench_add_custom_attribute(self):
        add_custom_attribute("key", "value")

    @background_task()
    def bench_add_custom_attributes(self):
        add_custom_attributes([("key1", "value1"), ("key2", "value2")])

    @background_task()
    def bench_add_framework_info(self):
        add_framework_info("my_framework", (1, 2, 3))

    @background_task()
    def bench_transaction_name(self):
        @transaction_name("test_transaction_name")
        def test():
            pass

        test()

    @background_task()
    def bench_capture_request_params(self):
        capture_request_params(flag=True)


@benchmark
class TraceApis:
    @background_task()
    def bench_current_trace(self):
        current_trace()

    @background_task()
    def bench_current_trace_id(self):
        current_trace_id()

    @background_task()
    def bench_current_span_id(self):
        current_span_id()

    @background_task()
    def bench_add_custom_span_attribute(self):
        add_custom_span_attribute("key", "value")

    @background_task()
    def bench_get_linking_metadata(self):
        get_linking_metadata()


@benchmark
class GlobalApis:
    def bench_application(self):
        application()

    def bench_application_settings(self):
        application_settings()

    def bench_global_settings(self):
        global_settings()

    def bench_extra_settings(self):
        extra_settings("test")


# TODO: The setup for distributed tracing benchmarks is much more complicated.
# @benchmark
# class DistributedTracingApis:
#     @background_task()
#     def bench_accept_distributed_trace_headers(self):
#         accept_distributed_trace_headers()

#     @background_task()
#     def bench_accept_distributed_trace_payload(self):
#         accept_distributed_trace_payload()

#     @background_task()
#     def bench_create_distributed_trace_payload(self):
#         create_distributed_trace_payload()

#     @background_task()
#     def bench_insert_distributed_trace_headers(self):
#         insert_distributed_trace_headers()


@benchmark
class BrowserApis:
    TEST_BROWSER_HTML = b"""
    <head>
    </head>
    <body>
    Content
    </body>
    """

    @web_transaction()
    def bench_get_browser_timing_header(self):
        get_browser_timing_header()

    @web_transaction()
    def bench_insert_html_snippet(self):
        modified_body = insert_html_snippet(
            self.TEST_BROWSER_HTML, lambda: get_browser_timing_header().encode("latin-1")
        )
        assert modified_body != self.TEST_BROWSER_HTML

    @web_transaction()
    def bench_verify_body_exists(self):
        assert verify_body_exists(self.TEST_BROWSER_HTML)
