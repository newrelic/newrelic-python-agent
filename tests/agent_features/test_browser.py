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

import json
import sys

import six
import webtest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_custom_parameters import (
    validate_custom_parameters,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)

from newrelic.api.application import application_settings
from newrelic.api.transaction import (
    add_custom_attribute,
    disable_browser_autorum,
    get_browser_timing_footer,
    get_browser_timing_header,
)
from newrelic.api.wsgi_application import wsgi_application
from newrelic.common.encoding_utils import deobfuscate

_runtime_error_name = RuntimeError.__module__ + ":" + RuntimeError.__name__


@wsgi_application()
def target_wsgi_application_manual_rum(environ, start_response):
    status = "200 OK"

    text = "<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>"

    output = (text % (get_browser_timing_header(), get_browser_timing_footer())).encode("UTF-8")

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    return [output]


target_application_manual_rum = webtest.TestApp(target_wsgi_application_manual_rum)

_test_footer_attributes = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": False,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_footer_attributes)
def test_footer_attributes():
    settings = application_settings()

    assert settings.browser_monitoring.enabled

    assert settings.browser_key
    assert settings.browser_monitoring.loader_version
    assert settings.js_agent_loader
    assert isinstance(settings.js_agent_file, six.string_types)
    assert settings.beacon
    assert settings.error_beacon

    token = "0123456789ABCDEF"  # nosec
    headers = {"Cookie": "NRAGENT=tk=%s" % token}

    response = target_application_manual_rum.get("/", headers=headers)

    header = response.html.html.head.script.string
    content = response.html.html.body.p.string
    footer = response.html.html.body.script.string

    # Validate actual body content.

    assert content == "RESPONSE"

    # Validate the insertion of RUM header.

    assert header.find("NREUM HEADER") != -1

    # Now validate the various fields of the footer. The fields are
    # held by a JSON dictionary.

    data = json.loads(footer.split("NREUM.info=")[1])

    assert data["licenseKey"] == settings.browser_key
    assert data["applicationID"] == settings.application_id

    assert data["agent"] == settings.js_agent_file
    assert data["beacon"] == settings.beacon
    assert data["errorBeacon"] == settings.error_beacon

    assert data["applicationTime"] >= 0
    assert data["queueTime"] >= 0

    obfuscation_key = settings.license_key[:13]

    type_transaction_data = unicode if six.PY2 else str  # noqa: F821
    assert isinstance(data["transactionName"], type_transaction_data)

    txn_name = deobfuscate(data["transactionName"], obfuscation_key)

    assert txn_name == "WebTransaction/Uri/"

    assert "atts" not in data


_test_rum_ssl_for_http_is_none = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": False,
    "browser_monitoring.ssl_for_http": None,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_rum_ssl_for_http_is_none)
def test_ssl_for_http_is_none():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is None

    response = target_application_manual_rum.get("/")
    footer = response.html.html.body.script.string
    data = json.loads(footer.split("NREUM.info=")[1])

    assert "sslForHttp" not in data


_test_rum_ssl_for_http_is_true = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": False,
    "browser_monitoring.ssl_for_http": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_rum_ssl_for_http_is_true)
def test_ssl_for_http_is_true():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is True

    response = target_application_manual_rum.get("/")
    footer = response.html.html.body.script.string
    data = json.loads(footer.split("NREUM.info=")[1])

    assert data["sslForHttp"] is True


_test_rum_ssl_for_http_is_false = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": False,
    "browser_monitoring.ssl_for_http": False,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_rum_ssl_for_http_is_false)
def test_ssl_for_http_is_false():
    settings = application_settings()

    assert settings.browser_monitoring.ssl_for_http is False

    response = target_application_manual_rum.get("/")
    footer = response.html.html.body.script.string
    data = json.loads(footer.split("NREUM.info=")[1])

    assert data["sslForHttp"] is False


@wsgi_application()
def target_wsgi_application_yield_single_no_head(environ, start_response):
    status = "200 OK"

    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    yield output


target_application_yield_single_no_head = webtest.TestApp(target_wsgi_application_yield_single_no_head)

_test_html_insertion_yield_single_no_head_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_single_no_head_settings)
def test_html_insertion_yield_single_no_head():
    response = target_application_yield_single_no_head.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain("NREUM HEADER", "NREUM.info")


@wsgi_application()
def target_wsgi_application_yield_multi_no_head(environ, start_response):
    status = "200 OK"

    output = [b"<html>", b"<body><p>RESPONSE</p></body></html>"]

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(b"".join(output))))]
    start_response(status, response_headers)

    for data in output:
        yield data


target_application_yield_multi_no_head = webtest.TestApp(target_wsgi_application_yield_multi_no_head)

_test_html_insertion_yield_multi_no_head_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_multi_no_head_settings)
def test_html_insertion_yield_multi_no_head():
    response = target_application_yield_multi_no_head.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain("NREUM HEADER", "NREUM.info")


@wsgi_application()
def target_wsgi_application_unnamed_attachment_header(environ, start_response):
    status = "200 OK"

    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(output))),
        ("Content-Disposition", "attachment"),
    ]
    start_response(status, response_headers)

    yield output


target_application_unnamed_attachment_header = webtest.TestApp(target_wsgi_application_unnamed_attachment_header)

_test_html_insertion_unnamed_attachment_header_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_unnamed_attachment_header_settings)
def test_html_insertion_unnamed_attachment_header():
    response = target_application_unnamed_attachment_header.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers
    assert "Content-Disposition" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_named_attachment_header(environ, start_response):
    status = "200 OK"

    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(output))),
        ("Content-Disposition", 'Attachment; filename="X"'),
    ]
    start_response(status, response_headers)

    yield output


target_application_named_attachment_header = webtest.TestApp(target_wsgi_application_named_attachment_header)

_test_html_insertion_named_attachment_header_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_named_attachment_header_settings)
def test_html_insertion_named_attachment_header():
    response = target_application_named_attachment_header.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers
    assert "Content-Disposition" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_inline_attachment_header(environ, start_response):
    status = "200 OK"

    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(output))),
        ("Content-Disposition", 'inline; filename="attachment"'),
    ]
    start_response(status, response_headers)

    yield output


target_application_inline_attachment_header = webtest.TestApp(target_wsgi_application_inline_attachment_header)

_test_html_insertion_inline_attachment_header_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_inline_attachment_header_settings)
def test_html_insertion_inline_attachment_header():
    response = target_application_inline_attachment_header.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers
    assert "Content-Disposition" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain("NREUM HEADER", "NREUM.info")


@wsgi_application()
def target_wsgi_application_empty_list(environ, start_response):
    status = "200 OK"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", "0")]
    start_response(status, response_headers)

    return []


target_application_empty_list = webtest.TestApp(target_wsgi_application_empty_list)

_test_html_insertion_empty_list_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_empty_list_settings)
def test_html_insertion_empty_list():
    response = target_application_empty_list.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    assert len(response.body) == 0


@wsgi_application()
def target_wsgi_application_single_empty_string(environ, start_response):
    status = "200 OK"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", "0")]
    start_response(status, response_headers)

    return [""]


target_application_single_empty_string = webtest.TestApp(target_wsgi_application_single_empty_string)

_test_html_insertion_single_empty_string_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_single_empty_string_settings)
def test_html_insertion_single_empty_string():
    response = target_application_single_empty_string.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    assert len(response.body) == 0


@wsgi_application()
def target_wsgi_application_multiple_empty_string(environ, start_response):
    status = "200 OK"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", "0")]
    start_response(status, response_headers)

    return ["", ""]


target_application_multiple_empty_string = webtest.TestApp(target_wsgi_application_multiple_empty_string)

_test_html_insertion_multiple_empty_string_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_multiple_empty_string_settings)
def test_html_insertion_multiple_empty_string():
    response = target_application_multiple_empty_string.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    assert len(response.body) == 0


@wsgi_application()
def target_wsgi_application_single_large_prelude(environ, start_response):
    status = "200 OK"

    output = [64 * 1024 * b" " + b"<body></body>"]

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(b"".join(output))))]
    start_response(status, response_headers)

    return output


target_application_single_large_prelude = webtest.TestApp(target_wsgi_application_single_large_prelude)

_test_html_insertion_single_large_prelude_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_single_large_prelude_settings)
def test_html_insertion_single_large_prelude():
    response = target_application_single_large_prelude.get("/", status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    output = [32 * 1024 * b" ", 32 * 1024 * b" ", b"<body></body>"]

    assert len(response.body) == len(b"".join(output))


@wsgi_application()
def target_wsgi_application_multi_large_prelude(environ, start_response):
    status = "200 OK"

    output = [32 * 1024 * b" ", 32 * 1024 * b" ", b"<body></body>"]

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(b"".join(output))))]
    start_response(status, response_headers)

    return output


target_application_multi_large_prelude = webtest.TestApp(target_wsgi_application_multi_large_prelude)

_test_html_insertion_multi_large_prelude_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_multi_large_prelude_settings)
def test_html_insertion_multi_large_prelude():
    response = target_application_multi_large_prelude.get("/", status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    output = [32 * 1024 * b" ", 32 * 1024 * b" ", b"<body></body>"]

    assert len(response.body) == len(b"".join(output))


@wsgi_application()
def target_wsgi_application_yield_before_start(environ, start_response):
    status = "200 OK"

    # Ambiguous whether yield an empty string before calling
    # start_response() is legal. Various WSGI servers allow it
    # We have to disable WebTest lint check to get this to run.

    yield b""

    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    yield output


target_application_yield_before_start = webtest.TestApp(target_wsgi_application_yield_before_start, lint=False)

_test_html_insertion_yield_before_start_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_before_start_settings)
def test_html_insertion_yield_before_start():
    response = target_application_yield_before_start.get("/", status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain("NREUM HEADER", "NREUM.info")


@wsgi_application()
def target_wsgi_application_start_yield_start(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]

    start_response("200 OK", response_headers)

    yield ""

    try:
        start_response(status, response_headers)  # noqa: F821
    except Exception:
        start_response("500 Error", response_headers, sys.exc_info())

    yield output


target_application_start_yield_start = webtest.TestApp(target_wsgi_application_start_yield_start)

_test_html_insertion_start_yield_start_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_start_yield_start_settings)
def test_html_insertion_start_yield_start():
    response = target_application_start_yield_start.get("/", status=500)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain("NREUM HEADER", "NREUM.info")


@wsgi_application()
def target_wsgi_application_invalid_content_length(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", "XXX")]

    start_response("200 OK", response_headers)

    yield output


target_application_invalid_content_length = webtest.TestApp(target_wsgi_application_invalid_content_length)

_test_html_insertion_invalid_content_length_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_invalid_content_length_settings)
def test_html_insertion_invalid_content_length():
    response = target_application_invalid_content_length.get("/", status=200)

    # This is relying on WebTest not validating the
    # value of the Content-Length response header
    # and just passing it through as is.

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    assert response.headers["Content-Length"] == "XXX"

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_content_encoding(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(output))),
        ("Content-Encoding", "identity"),
    ]

    start_response("200 OK", response_headers)

    yield output


target_application_content_encoding = webtest.TestApp(target_wsgi_application_content_encoding)

_test_html_insertion_content_encoding_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_content_encoding_settings)
def test_html_insertion_content_encoding():
    response = target_application_content_encoding.get("/", status=200)

    # Technically 'identity' should not be used in Content-Encoding
    # but clients will still accept it. Use this fact to disable auto
    # RUM for this test. Other option is to compress the response
    # and use 'gzip'.

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    assert response.headers["Content-Encoding"] == "identity"

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_no_content_type(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Length", str(len(output)))]

    start_response("200 OK", response_headers)

    yield output


target_application_no_content_type = webtest.TestApp(target_wsgi_application_no_content_type, lint=False)

_test_html_insertion_no_content_type_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_no_content_type_settings)
def test_html_insertion_no_content_type():
    response = target_application_no_content_type.get("/", status=200)

    assert "Content-Type" not in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_plain_text(environ, start_response):
    output = b"RESPONSE"

    response_headers = [("Content-Type", "text/plain"), ("Content-Length", str(len(output)))]

    start_response("200 OK", response_headers)

    yield output


target_application_plain_text = webtest.TestApp(target_wsgi_application_plain_text)

_test_html_insertion_plain_text_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_plain_text_settings)
def test_html_insertion_plain_text():
    response = target_application_plain_text.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_write_callback(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html"), ("Content-Length", str(len(output)))]

    write = start_response("200 OK", response_headers)

    write(output)

    return []


target_application_write_callback = webtest.TestApp(target_wsgi_application_write_callback)

_test_html_insertion_write_callback_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_write_callback_settings)
def test_html_insertion_write_callback():
    response = target_application_write_callback.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_yield_before_write(environ, start_response):
    output = [b"<html>", b"<body><p>RESPONSE</p></body></html>"]

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(b"".join(output))))]

    write = start_response("200 OK", response_headers)

    # Technically this is in violation of the WSGI specification
    # if that write() should always be before yields.

    yield output.pop(0)

    write(output.pop(0))


target_application_yield_before_write = webtest.TestApp(target_wsgi_application_yield_before_write)

_test_html_insertion_yield_before_write_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_before_write_settings)
def test_html_insertion_yield_before_write():
    response = target_application_yield_before_write.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    expected = b"<html><body><p>RESPONSE</p></body></html>"

    assert response.body == expected


@wsgi_application()
def target_wsgi_application_write_before_yield(environ, start_response):
    output = [b"<html>", b"<body><p>RESPONSE</p></body></html>"]

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(b"".join(output))))]

    write = start_response("200 OK", response_headers)

    write(output.pop(0))

    yield output.pop(0)


target_application_write_before_yield = webtest.TestApp(target_wsgi_application_write_before_yield)

_test_html_insertion_write_before_yield_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_write_before_yield_settings)
def test_html_insertion_write_before_yield():
    response = target_application_write_before_yield.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])

    expected = b"<html><body><p>RESPONSE</p></body></html>"

    assert response.body == expected


@wsgi_application()
def target_wsgi_application_param_on_close(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]

    start_response("200 OK", response_headers)

    try:
        yield output

    finally:
        add_custom_attribute("key", "value")


target_application_param_on_close = webtest.TestApp(target_wsgi_application_param_on_close)

_test_html_insertion_param_on_close_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_param_on_close_settings)
@validate_custom_parameters(required_params=[("key", "value")])
def test_html_insertion_param_on_close():
    response = target_application_param_on_close.get("/", status=200)

    response.mustcontain("NREUM HEADER", "NREUM.info")


@wsgi_application()
def target_wsgi_application_param_on_error(environ, start_response):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]

    start_response("200 OK", response_headers)

    try:
        raise RuntimeError("ERROR")

        yield output

    finally:
        add_custom_attribute("key", "value")


target_application_param_on_error = webtest.TestApp(target_wsgi_application_param_on_error)

_test_html_insertion_param_on_error_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_param_on_error_settings)
@validate_transaction_errors(errors=[_runtime_error_name])
@validate_custom_parameters(required_params=[("key", "value")])
def test_html_insertion_param_on_error():
    try:
        response = target_application_param_on_error.get("/", status=500)

    except RuntimeError:
        pass


@wsgi_application()
def target_wsgi_application_disable_autorum_via_api(environ, start_response):
    status = "200 OK"

    output = b"<html><body><p>RESPONSE</p></body></html>"

    disable_browser_autorum()

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    yield output


target_application_disable_autorum_via_api = webtest.TestApp(target_wsgi_application_disable_autorum_via_api)

_test_html_insertion_disable_autorum_via_api_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_disable_autorum_via_api_settings)
def test_html_insertion_disable_autorum_via_api():
    response = target_application_disable_autorum_via_api.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])


@wsgi_application()
def target_wsgi_application_manual_rum_insertion(environ, start_response):
    status = "200 OK"

    output = b"<html><body><p>RESPONSE</p></body></html>"

    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    assert header == ""
    assert footer == ""

    response_headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    yield output


target_application_manual_rum_insertion = webtest.TestApp(target_wsgi_application_manual_rum_insertion)

_test_html_insertion_manual_rum_insertion_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_manual_rum_insertion_settings)
def test_html_insertion_manual_rum_insertion():
    response = target_application_manual_rum_insertion.get("/", status=200)

    assert "Content-Type" in response.headers
    assert "Content-Length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain(no=["NREUM HEADER", "NREUM.info"])
