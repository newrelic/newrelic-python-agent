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

import pytest
import six
from bs4 import BeautifulSoup
from testing_support.asgi_testing import AsgiTest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_custom_parameters import (
    validate_custom_parameters,
)
from testing_support.validators.validate_transaction_errors import (
    validate_transaction_errors,
)

from newrelic.api.application import application_settings
from newrelic.api.asgi_application import asgi_application
from newrelic.api.transaction import (
    add_custom_attribute,
    disable_browser_autorum,
    get_browser_timing_footer,
    get_browser_timing_header,
)
from newrelic.common.encoding_utils import deobfuscate

_runtime_error_name = RuntimeError.__module__ + ":" + RuntimeError.__name__


@asgi_application()
async def target_asgi_application_manual_rum(scope, receive, send):
    text = "<html><head>%s</head><body><p>RESPONSE</p>%s</body></html>"

    output = (text % (get_browser_timing_header(), get_browser_timing_footer())).encode("UTF-8")

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_manual_rum = AsgiTest(target_asgi_application_manual_rum)

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

    html = BeautifulSoup(response.body, "html.parser")
    header = html.html.head.script.string
    content = html.html.body.p.string
    footer = html.html.body.script.string

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

    type_transaction_data = unicode if six.PY2 else str  # noqa: F821, pylint: disable=E0602
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
    html = BeautifulSoup(response.body, "html.parser")
    footer = html.html.body.script.string
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
    html = BeautifulSoup(response.body, "html.parser")
    footer = html.html.body.script.string
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
    html = BeautifulSoup(response.body, "html.parser")
    footer = html.html.body.script.string
    data = json.loads(footer.split("NREUM.info=")[1])

    assert data["sslForHttp"] is False


@asgi_application()
async def target_asgi_application_yield_single_no_head(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_yield_single_no_head = AsgiTest(target_asgi_application_yield_single_no_head)

_test_html_insertion_yield_single_no_head_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_single_no_head_settings)
def test_html_insertion_yield_single_no_head():
    response = target_application_yield_single_no_head.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" in response.body
    assert b"NREUM.info" in response.body


@asgi_application()
async def target_asgi_application_yield_multi_no_head(scope, receive, send):
    output = [b"<html>", b"<body><p>RESPONSE</p></body></html>"]

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(b"".join(output))).encode("utf-8")),
    ]
    await send({"type": "http.response.start", "status": 200, "headers": response_headers})

    for data in output:
        more_body = data is not output[-1]
        await send({"type": "http.response.body", "body": data, "more_body": more_body})


target_application_yield_multi_no_head = AsgiTest(target_asgi_application_yield_multi_no_head)

_test_html_insertion_yield_multi_no_head_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_multi_no_head_settings)
def test_html_insertion_yield_multi_no_head():
    response = target_application_yield_multi_no_head.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" in response.body
    assert b"NREUM.info" in response.body


@asgi_application()
async def target_asgi_application_unnamed_attachment_header(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
        (b"content-disposition", b"attachment"),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_unnamed_attachment_header = AsgiTest(target_asgi_application_unnamed_attachment_header)

_test_html_insertion_unnamed_attachment_header_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_unnamed_attachment_header_settings)
def test_html_insertion_unnamed_attachment_header():
    response = target_application_unnamed_attachment_header.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers
    assert "content-disposition" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_named_attachment_header(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
        (b"content-disposition", b'Attachment; filename="X"'),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_named_attachment_header = AsgiTest(target_asgi_application_named_attachment_header)

_test_html_insertion_named_attachment_header_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_named_attachment_header_settings)
def test_html_insertion_named_attachment_header():
    response = target_application_named_attachment_header.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers
    assert "content-disposition" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_inline_attachment_header(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
        (b"content-disposition", b'inline; filename="attachment"'),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_inline_attachment_header = AsgiTest(target_asgi_application_inline_attachment_header)

_test_html_insertion_inline_attachment_header_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_inline_attachment_header_settings)
def test_html_insertion_inline_attachment_header():
    response = target_application_inline_attachment_header.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers
    assert "content-disposition" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" in response.body
    assert b"NREUM.info" in response.body


@asgi_application()
async def target_asgi_application_empty(scope, receive, send):
    status = "200 OK"

    response_headers = [(b"content-type", b"text/html; charset=utf-8"), (b"content-length", b"0")]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body"})


target_application_empty = AsgiTest(target_asgi_application_empty)

_test_html_insertion_empty_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_empty_settings)
def test_html_insertion_empty():
    response = target_application_empty.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body

    assert len(response.body) == 0


@asgi_application()
async def target_asgi_application_single_empty_string(scope, receive, send):
    response_headers = [(b"content-type", b"text/html; charset=utf-8"), (b"content-length", b"0")]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": b""})


target_application_single_empty_string = AsgiTest(target_asgi_application_single_empty_string)

_test_html_insertion_single_empty_string_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_single_empty_string_settings)
def test_html_insertion_single_empty_string():
    response = target_application_single_empty_string.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body

    assert len(response.body) == 0


@asgi_application()
async def target_asgi_application_multiple_empty_string(scope, receive, send):
    response_headers = [(b"content-type", b"text/html; charset=utf-8"), (b"content-length", b"0")]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": b"", "more_body": True})
    await send({"type": "http.response.body", "body": b""})


target_application_multiple_empty_string = AsgiTest(target_asgi_application_multiple_empty_string)

_test_html_insertion_multiple_empty_string_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_multiple_empty_string_settings)
def test_html_insertion_multiple_empty_string():
    response = target_application_multiple_empty_string.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body

    assert len(response.body) == 0


@asgi_application()
async def target_asgi_application_single_large_prelude(scope, receive, send):
    output = 64 * 1024 * b" " + b"<body></body>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_single_large_prelude = AsgiTest(target_asgi_application_single_large_prelude)

_test_html_insertion_single_large_prelude_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_single_large_prelude_settings)
def test_html_insertion_single_large_prelude():
    response = target_application_single_large_prelude.get("/")
    assert response.status == 200

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body

    output = [32 * 1024 * b" ", 32 * 1024 * b" ", b"<body></body>"]

    assert len(response.body) == len(b"".join(output))


@asgi_application()
async def target_asgi_application_multi_large_prelude(scope, receive, send):
    output = [32 * 1024 * b" ", 32 * 1024 * b" ", b"<body></body>"]

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(b"".join(output))).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    for data in output:
        more_body = data is not output[-1]
        await send({"type": "http.response.body", "body": data, "more_body": more_body})


target_application_multi_large_prelude = AsgiTest(target_asgi_application_multi_large_prelude)

_test_html_insertion_multi_large_prelude_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_multi_large_prelude_settings)
def test_html_insertion_multi_large_prelude():
    response = target_application_multi_large_prelude.get("/")
    assert response.status == 200

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body

    output = [32 * 1024 * b" ", 32 * 1024 * b" ", b"<body></body>"]

    assert len(response.body) == len(b"".join(output))


@asgi_application()
async def target_asgi_application_yield_before_start(scope, receive, send):
    # This is not legal but we should see what happens with our middleware
    await send({"type": "http.response.body", "body": b"", "more_body": True})

    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_yield_before_start = AsgiTest(target_asgi_application_yield_before_start)

_test_html_insertion_yield_before_start_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_yield_before_start_settings)
def test_html_insertion_yield_before_start():
    # The application should complete as pass through, but an assertion error
    # would be raised in the AsgiTest class
    with pytest.raises(AssertionError):
        target_application_yield_before_start.get("/")


@asgi_application()
async def target_asgi_application_start_yield_start(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": b""})
    await send({"type": "http.response.start", "status": 200, "headers": response_headers})


target_application_start_yield_start = AsgiTest(target_asgi_application_start_yield_start)

_test_html_insertion_start_yield_start_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_start_yield_start_settings)
def test_html_insertion_start_yield_start():
    # The application should complete as pass through, but an assertion error
    # would be raised in the AsgiTest class
    with pytest.raises(AssertionError):
        target_application_start_yield_start.get("/")


@asgi_application()
async def target_asgi_application_invalid_content_length(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [(b"content-type", b"text/html; charset=utf-8"), (b"content-length", b"XXX")]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_invalid_content_length = AsgiTest(target_asgi_application_invalid_content_length)

_test_html_insertion_invalid_content_length_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_invalid_content_length_settings)
def test_html_insertion_invalid_content_length():
    response = target_application_invalid_content_length.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    assert response.headers["content-length"] == "XXX"

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_content_encoding(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
        (b"content-encoding", b"identity"),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_content_encoding = AsgiTest(target_asgi_application_content_encoding)

_test_html_insertion_content_encoding_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_content_encoding_settings)
def test_html_insertion_content_encoding():
    response = target_application_content_encoding.get("/")
    assert response.status == 200

    # Technically 'identity' should not be used in Content-Encoding
    # but clients will still accept it. Use this fact to disable auto
    # RUM for this test. Other option is to compress the response
    # and use 'gzip'.

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    assert response.headers["content-encoding"] == "identity"

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_no_content_type(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [(b"content-length", str(len(output)).encode("utf-8"))]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_no_content_type = AsgiTest(target_asgi_application_no_content_type)

_test_html_insertion_no_content_type_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_no_content_type_settings)
def test_html_insertion_no_content_type():
    response = target_application_no_content_type.get("/")
    assert response.status == 200

    assert "content-type" not in response.headers
    assert "content-length" in response.headers

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_plain_text(scope, receive, send):
    output = b"RESPONSE"

    response_headers = [(b"content-type", b"text/plain"), (b"content-length", str(len(output)).encode("utf-8"))]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_plain_text = AsgiTest(target_asgi_application_plain_text)

_test_html_insertion_plain_text_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_plain_text_settings)
def test_html_insertion_plain_text():
    response = target_application_plain_text.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_param(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    add_custom_attribute("key", "value")
    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_param = AsgiTest(target_asgi_application_param)


_test_html_insertion_param_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_param_settings)
@validate_custom_parameters(required_params=[("key", "value")])
def test_html_insertion_param():
    response = target_application_param.get("/")
    assert response.status == 200

    assert b"NREUM HEADER" in response.body
    assert b"NREUM.info" in response.body


@asgi_application()
async def target_asgi_application_param_on_error(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})

    try:
        raise RuntimeError("ERROR")
    finally:
        add_custom_attribute("key", "value")


target_application_param_on_error = AsgiTest(target_asgi_application_param_on_error)

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
        target_application_param_on_error.get("/")
    except RuntimeError:
        pass


@asgi_application()
async def target_asgi_application_disable_autorum_via_api(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    disable_browser_autorum()

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_disable_autorum_via_api = AsgiTest(target_asgi_application_disable_autorum_via_api)

_test_html_insertion_disable_autorum_via_api_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_disable_autorum_via_api_settings)
def test_html_insertion_disable_autorum_via_api():
    response = target_application_disable_autorum_via_api.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body


@asgi_application()
async def target_asgi_application_manual_rum_insertion(scope, receive, send):
    output = b"<html><body><p>RESPONSE</p></body></html>"

    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    header = get_browser_timing_header()
    footer = get_browser_timing_footer()

    assert header == ""
    assert footer == ""

    response_headers = [
        (b"content-type", b"text/html; charset=utf-8"),
        (b"content-length", str(len(output)).encode("utf-8")),
    ]

    await send({"type": "http.response.start", "status": 200, "headers": response_headers})
    await send({"type": "http.response.body", "body": output})


target_application_manual_rum_insertion = AsgiTest(target_asgi_application_manual_rum_insertion)

_test_html_insertion_manual_rum_insertion_settings = {
    "browser_monitoring.enabled": True,
    "browser_monitoring.auto_instrument": True,
    "js_agent_loader": "<!-- NREUM HEADER -->",
}


@override_application_settings(_test_html_insertion_manual_rum_insertion_settings)
def test_html_insertion_manual_rum_insertion():
    response = target_application_manual_rum_insertion.get("/")
    assert response.status == 200

    assert "content-type" in response.headers
    assert "content-length" in response.headers

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    assert b"NREUM HEADER" not in response.body
    assert b"NREUM.info" not in response.body
