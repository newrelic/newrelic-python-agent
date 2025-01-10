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

"""
This file tests Flask where instrumentation is enabled for both New Relic and
OpenTelemetry.  There are three primary scenarios to consider:
1. Overlapping instrumentation points which we will want New Relic to supersede.
2. Instrumentation points that are covered by OpenTelemetry but not New Relic.
3. Instrumentation points that are covered by New Relic but not OpenTelemetry.
"""

import pytest
from testing_support.fixtures import dt_enabled, override_application_settings
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)
from testing_support.validators.validate_transaction_event_attributes import (
    validate_transaction_event_attributes,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)


def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late.

    from _test_flask import _test_flask_application

    return _test_flask_application


_test_flask_index_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:index_page", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
]

_test_flask_index_otel_metrics = [
    ("Otel/GET /index", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_index(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings(
        {
            "otel_dimensional_metrics.enabled": setting_override,
            "attributes.include": ["request.*"],
        }
    )
    @dt_enabled
    @validate_transaction_event_attributes(
        required_params={
            "agent": [
                "request.headers.host",
                "request.uri",
                "response.status",
                "response.headers.contentType",
                "response.headers.contentLength",
            ],
            "user": [],
            "intrinsic": ["port"],
        },
        exact_attrs={
            "agent": {
                "request.uri": "/index",
                "response.status": "200",
                "response.headers.contentType": "text/html; charset=utf-8",
            },
            "user": {},
            "intrinsic": {},
        },
    )
    @validate_transaction_metrics(
        name="_test_flask:index_page",
        scoped_metrics=_test_flask_index_scoped_metrics + _test_flask_index_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    @validate_span_events(
        count=1,
        expected_users=["http.url", "net.host.name", "http.host", "net.host.port"],
        exact_users={
            "http.scheme": "http",
            "span.kind": "SpanKind.SERVER",
            "http.method": "GET",
            "http.server_name": "localhost",
        },
    )
    def _test():
        application = target_application()
        response = application.get("/index")
        response.mustcontain("INDEX RESPONSE")

    _test()


_test_flask_async_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:async_page", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
]

_test_flask_async_otel_metrics = [
    ("Otel/GET /async", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_async(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_metrics(
        "_test_flask:async_page",
        scoped_metrics=_test_flask_async_scoped_metrics + _test_flask_async_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        response = application.get("/async")
        response.mustcontain("ASYNC RESPONSE")

    _test()


_test_flask_endpoint_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:endpoint_page", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
]

_test_flask_endpoint_otel_metrics = [
    ("Otel/GET /endpoint", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_endpoint(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_metrics(
        "_test_flask:endpoint_page",
        scoped_metrics=_test_flask_endpoint_scoped_metrics + _test_flask_endpoint_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        response = application.get("/endpoint")
        response.mustcontain("ENDPOINT RESPONSE")

    _test()


_test_flask_error_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:error_page", 1),
    ("Function/flask.app:Flask.handle_exception", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
    ("Function/flask.app:Flask.handle_user_exception", 1),
    ("Function/flask.app:Flask.handle_user_exception", 1),
]

_test_flask_error_otel_metrics = [
    ("Otel/GET /error", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_error(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_errors(errors=["builtins:RuntimeError"])
    @validate_transaction_metrics(
        "_test_flask:error_page",
        scoped_metrics=_test_flask_error_scoped_metrics + _test_flask_error_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        application.get("/error", status=500)

    _test()


_test_flask_abort_404_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:abort_404_page", 1),
    ("Function/flask.app:Flask.handle_http_exception", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
    ("Function/flask.app:Flask.handle_user_exception", 1),
]

_test_flask_abort_404_otel_metrics = [
    ("Otel/GET /abort_404", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_abort_404(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_metrics(
        "_test_flask:abort_404_page",
        scoped_metrics=_test_flask_abort_404_scoped_metrics + _test_flask_abort_404_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        application.get("/abort_404", status=404)

    _test()


_test_flask_exception_404_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:exception_404_page", 1),
    ("Function/flask.app:Flask.handle_http_exception", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
    ("Function/flask.app:Flask.handle_user_exception", 1),
]

_test_flask_exception_404_otel_metrics = [
    ("Otel/GET /exception_404", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_exception_404(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_metrics(
        "_test_flask:exception_404_page",
        scoped_metrics=_test_flask_exception_404_scoped_metrics + _test_flask_exception_404_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        application.get("/exception_404", status=404)

    _test()


_test_flask_not_found_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/flask.app:Flask.handle_http_exception", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
    ("Function/flask.app:Flask.handle_user_exception", 1),
]

_test_flask_not_found_otel_metrics = [
    ("Otel/GET /missing", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_not_found(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_metrics(
        "flask.app:Flask.handle_http_exception",
        scoped_metrics=_test_flask_not_found_scoped_metrics + _test_flask_not_found_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        application.get("/missing", status=404)

    _test()


_test_flask_render_template_string_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:template_string", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
    ("Template/Compile/<template>", 1),
    ("Template/Render/<template>", 1),
]

_test_flask_render_template_string_otel_metrics = [
    ("Otel/GET /template_string", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_render_template_string(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_metrics(
        "_test_flask:template_string",
        scoped_metrics=_test_flask_render_template_string_scoped_metrics
        + _test_flask_render_template_string_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        application.get("/template_string")

    _test()


_test_flask_render_template_not_found_scoped_metrics = [
    ("Function/flask.app:Flask.wsgi_app", 1),
    ("Python/WSGI/Application", 1),
    ("Python/WSGI/Response", 1),
    ("Python/WSGI/Finalize", 1),
    ("Function/_test_flask:template_not_found", 1),
    ("Function/flask.app:Flask.handle_exception", 1),
    ("Function/werkzeug.wsgi:ClosingIterator.close", 1),
    ("Function/flask.app:Flask.handle_user_exception", 1),
]

_test_flask_render_template_not_found_otel_metrics = [
    ("Otel/GET /template_not_found", 1),
]


@pytest.mark.parametrize(
    "setting_override,custom_metrics,dimensional_metrics",
    [
        (
            False,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", -1),
            ],
            None,
        ),
        (
            True,
            None,
            [
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.duration", None, 1),
                ("OtelMeter/opentelemetry.instrumentation.flask/http.server.active_requests", None, -1),
            ],
        ),
    ],
)
def test_flask_render_template_not_found(setting_override, custom_metrics, dimensional_metrics):
    @override_application_settings({"otel_dimensional_metrics.enabled": setting_override})
    @validate_transaction_errors(errors=["jinja2.exceptions:TemplateNotFound"])
    @validate_transaction_metrics(
        "_test_flask:template_not_found",
        scoped_metrics=_test_flask_render_template_not_found_scoped_metrics
        + _test_flask_render_template_not_found_otel_metrics,
        custom_metrics=custom_metrics,
        dimensional_metrics=dimensional_metrics,
    )
    def _test():
        application = target_application()
        application.get("/template_not_found", status=500, expect_errors=True)

    _test()


_test_html_insertion_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_settings)
def test_flask_html_insertion():
    application = target_application()
    response = application.get("/html_insertion", status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # header added by the agent.

    response.mustcontain("NREUM HEADER", "NREUM.info")
