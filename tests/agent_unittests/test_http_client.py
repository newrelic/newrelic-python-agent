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

import base64
import json
import os.path
import ssl
import zlib

import pytest
from testing_support.mock_external_http_server import (
    BaseHTTPServer,
    MockExternalHTTPServer,
)

from newrelic.common import certs
from newrelic.common.agent_http import (
    ApplicationModeClient,
    DeveloperModeClient,
    HttpClient,
    InsecureHttpClient,
    ServerlessModeClient,
)
from newrelic.common.encoding_utils import ensure_str
from newrelic.common.object_names import callable_name
from newrelic.core.internal_metrics import InternalTraceContext
from newrelic.core.stats_engine import CustomMetrics
from newrelic.network.exceptions import NetworkInterfaceException
from newrelic.packages.urllib3.util import Url

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


SERVER_CERT = os.path.join(os.path.dirname(__file__), "cert.pem")


def echo_full_request(self):
    self.server.connections.append(self.connection)
    request_line = str(self.requestline).encode("utf-8")
    headers = "\n".join("%s: %s" % (k.lower(), v) for k, v in self.headers.items())
    self.send_response(200)
    self.end_headers()
    self.wfile.write(request_line)
    self.wfile.write(b"\n")
    self.wfile.write(headers.strip().encode("utf-8"))
    self.wfile.write(b"\n")
    content_length = int(self.headers.get("Content-Length", 0))
    if content_length:
        data = self.rfile.read(content_length)
        self.wfile.write(data)


class InsecureServer(MockExternalHTTPServer):
    def __init__(self, handler=echo_full_request, port=None, *args, **kwargs):
        super(MockExternalHTTPServer, self).__init__(*args, **kwargs)
        self.port = port or self.get_open_port()

        def do_CONNECT(self):
            host_port = self.requestline.split(" ", 2)[1]
            self.server.connect_host, self.server.connect_port = host_port.split(":", 1)
            self.server.connect_headers = self.headers

            self.send_response(200)
            self.end_headers()
            self.close_connection = True

        handler = type(
            "ResponseHandler",
            (
                BaseHTTPServer.BaseHTTPRequestHandler,
                object,
            ),
            {"do_GET": handler, "do_POST": handler, "do_CONNECT": do_CONNECT},
        )
        self.httpd = BaseHTTPServer.HTTPServer(("localhost", self.port), handler)
        self.httpd.connections = []
        self.httpd.connect_host = None
        self.httpd.connect_port = None
        self.httpd.connect_headers = {}
        self.daemon = True

    def reset(self):
        self.httpd.connect_host = None
        self.httpd.connect_port = None
        self.httpd.connect_headers = {}


class SecureServer(InsecureServer):
    def __init__(self, *args, **kwargs):
        super(SecureServer, self).__init__(*args, **kwargs)
        try:
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.context.load_cert_chain(certfile=SERVER_CERT, keyfile=SERVER_CERT)
            self.httpd.socket = self.context.wrap_socket(
                sock=self.httpd.socket,
                server_side=True,
                do_handshake_on_connect=False,
            )
        except (AttributeError, TypeError):
            self.httpd.socket = ssl.wrap_socket(
                self.httpd.socket,
                server_side=True,
                keyfile=SERVER_CERT,
                certfile=SERVER_CERT,
                do_handshake_on_connect=False,
            )


@pytest.fixture(scope="module")
def server():
    with SecureServer() as server:
        yield server


@pytest.fixture(scope="module")
def insecure_server():
    with InsecureServer() as server:
        yield server


@pytest.mark.parametrize(
    "scheme,host,port,username,password,expected",
    (
        (None, "host", 0, None, None, None),
        ("http", None, 8080, None, None, None),
        ("http", "host", 0, None, None, Url(scheme="http", host="host", port=None)),
        (
            "http",
            "host",
            8080,
            None,
            None,
            Url(scheme="http", host="host", port=8080),
        ),
        (
            "http",
            "https://host:8081",
            8080,
            None,
            None,
            Url(scheme="https", host="host", port=8081),
        ),
        (
            "http",
            "https://user:pass@host:8081",
            8080,
            None,
            None,
            Url(scheme="https", host="host", port=8081, auth="user:pass"),
        ),
        (
            "https",
            "host",
            8081,
            "username",
            None,
            Url(scheme="https", auth="username", host="host", port=8081),
        ),
        (
            "https",
            "host",
            8081,
            "username",
            "password",
            Url(scheme="https", auth="username:password", host="host", port=8081),
        ),
    ),
)
def test_proxy_parsing(scheme, host, port, username, password, expected):
    assert HttpClient._parse_proxy(scheme, host, port, username, password) == expected


@pytest.mark.parametrize("method", ("GET", "POST"))
def test_http_no_payload(server, method):
    with HttpClient("localhost", server.port, disable_certificate_validation=True) as client:
        connection = client._connection_attr
        status, data = client.send_request(method=method, headers={"foo": "bar"})

    assert status == 200
    data = ensure_str(data)
    data = data.split("\n")

    # Verify connection has been closed
    assert client._connection_attr is None
    assert connection.pool is None

    # Verify request line
    assert data[0].startswith(method + " /agent_listener/invoke_raw_method ")

    # Verify headers
    user_agent_header = ""
    foo_header = ""

    for header in data[1:-1]:
        if header.lower().startswith("user-agent:"):
            _, value = header.split(":", 1)
            value = value.strip()
            user_agent_header = value
        elif header.startswith("foo:"):
            _, value = header.split(":", 1)
            value = value.strip()
            foo_header = value

    assert user_agent_header.startswith("NewRelic-PythonAgent/")
    assert foo_header == "bar"


@pytest.mark.parametrize("client_cls", (HttpClient, ApplicationModeClient))
def test_non_ok_response(client_cls, server):
    internal_metrics = CustomMetrics()

    with client_cls("localhost", server.port, disable_certificate_validation=True) as client:
        with InternalTraceContext(internal_metrics):
            status, _ = client.send_request(method="PUT")

    assert status != 200
    internal_metrics = dict(internal_metrics.metrics())

    if client_cls is ApplicationModeClient:
        assert internal_metrics == {
            "Supportability/Python/Collector/Failures": [1, 0, 0, 0, 0, 0],
            "Supportability/Python/Collector/Failures/direct": [1, 0, 0, 0, 0, 0],
            "Supportability/Python/Collector/HTTPError/%d" % status: [1, 0, 0, 0, 0, 0],
        }
    else:
        assert not internal_metrics


def test_http_close_connection(server):
    client = HttpClient(
        "localhost",
        server.port,
        disable_certificate_validation=True,
    )

    status, _ = client.send_request()
    assert status == 200

    connection = client._connection_attr
    client.close_connection()
    assert client._connection_attr is None
    assert connection.pool is None

    # Verify that subsequent calls to close_connection don't crash
    client.close_connection()


def test_http_close_connection_in_context_manager():
    client = HttpClient("localhost", 1000)
    with client:
        client.close_connection()


@pytest.mark.parametrize(
    "client_cls,method,threshold",
    (
        (HttpClient, "gzip", 0),
        (HttpClient, "gzip", 100),
        (ApplicationModeClient, "gzip", 0),
        (ApplicationModeClient, "gzip", 100),
        (ApplicationModeClient, "deflate", 0),
        (ApplicationModeClient, "deflate", 100),
    ),
)
def test_http_payload_compression(server, client_cls, method, threshold):
    payload = b"*" * 20

    internal_metrics = CustomMetrics()

    with client_cls(
        "localhost",
        server.port,
        disable_certificate_validation=True,
        compression_method=method,
        compression_threshold=threshold,
    ) as client:
        with InternalTraceContext(internal_metrics):
            status, data = client.send_request(payload=payload, params={"method": "method1"})

    # Sending one additional request to valid metric aggregation for top level data usage supportability metrics
    with client_cls(
        "localhost",
        server.port,
        disable_certificate_validation=True,
        compression_method=method,
        compression_threshold=threshold,
    ) as client:
        with InternalTraceContext(internal_metrics):
            status, data = client.send_request(payload=payload, params={"method": "method2"})

    assert status == 200
    data = data.split(b"\n")
    sent_payload = data[-1]
    payload_byte_len = len(sent_payload)
    internal_metrics = dict(internal_metrics.metrics())
    if client_cls is ApplicationModeClient:
        assert internal_metrics["Supportability/Python/Collector/method1/Output/Bytes"][:2] == [
            1,
            len(payload),
        ]
        assert internal_metrics["Supportability/Python/Collector/Output/Bytes"][:2] == [
            2,
            len(payload)*2,
        ]

        if threshold < 20:
            # Verify compression time is recorded
            assert internal_metrics["Supportability/Python/Collector/method1/ZLIB/Compress"][0] == 1
            assert internal_metrics["Supportability/Python/Collector/method1/ZLIB/Compress"][1] > 0

            # Verify the compressed payload length is recorded
            assert internal_metrics["Supportability/Python/Collector/method1/ZLIB/Bytes"][:2] == [1, payload_byte_len]
            assert internal_metrics["Supportability/Python/Collector/ZLIB/Bytes"][:2] == [2, payload_byte_len*2]
            
            assert len(internal_metrics) == 8
        else:
            # Verify no ZLIB compression metrics were sent
            assert len(internal_metrics) == 3
    else:
        assert not internal_metrics

    if threshold < 20:
        expected_content_encoding = method.encode("utf-8")
        assert sent_payload != payload
        if method == "deflate":
            sent_payload = zlib.decompress(sent_payload)
        elif method == "gzip":
            decompressor = zlib.decompressobj(31)
            sent_payload = decompressor.decompress(sent_payload)
            sent_payload += decompressor.flush()
    else:
        expected_content_encoding = b"Identity"

    for header in data[1:-1]:
        if header.lower().startswith(b"content-encoding"):
            _, content_encoding = header.split(b":", 1)
            content_encoding = content_encoding.strip()
            break
    else:
        assert False, "Missing content-encoding header"

    assert content_encoding == expected_content_encoding
    assert sent_payload == payload


def test_cert_path(server):
    with HttpClient("localhost", server.port, ca_bundle_path=SERVER_CERT) as client:
        status, data = client.send_request()


@pytest.mark.parametrize("system_certs_available", (True, False))
def test_default_cert_path(monkeypatch, system_certs_available):
    if system_certs_available:
        cert_file = "foo"
    else:
        cert_file = None

    class DefaultVerifyPaths(object):
        cafile = cert_file

        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(ssl, "DefaultVerifyPaths", DefaultVerifyPaths)
    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        client = HttpClient("localhost", ca_bundle_path=None)

    internal_metrics = dict(internal_metrics.metrics())
    cert_metric = "Supportability/Python/Certificate/BundleRequired"
    if system_certs_available:
        assert "ca_certs" not in client._connection_kwargs
        assert cert_metric not in internal_metrics
    else:
        assert client._connection_kwargs["ca_certs"] == certs.where()
        assert internal_metrics[cert_metric][-3:-1] == [1, 1]


@pytest.mark.parametrize("auth", ((None, None), ("username", None), ("username", "password")))
def test_ssl_via_ssl_proxy(server, auth):
    proxy_user, proxy_pass = auth
    with HttpClient(
        "localhost",
        1,
        proxy_scheme="https",
        proxy_host="localhost",
        proxy_port=server.port,
        proxy_user=proxy_user,
        proxy_pass=proxy_pass,
        disable_certificate_validation=True,
    ) as client:
        status, data = client.send_request()

    assert status == 200
    data = data.decode("utf-8")
    data = data.split("\n")
    assert data[0].startswith("POST https://localhost:1/agent_listener/invoke_raw_method ")

    proxy_auth = None
    for header in data[1:-1]:
        if header.lower().startswith("proxy-authorization"):
            _, proxy_auth = header.split(":", 1)
            proxy_auth = proxy_auth.strip()
            break

    if proxy_user:
        auth_expected = proxy_user
        if proxy_pass:
            auth_expected = auth_expected + ":" + proxy_pass
        auth_expected = "Basic " + base64.b64encode(auth_expected.encode("utf-8")).decode("utf-8")
        assert proxy_auth == auth_expected
    else:
        assert not proxy_auth

    assert server.httpd.connect_host is None


def test_non_ssl_via_ssl_proxy(server):
    with InsecureHttpClient(
        "localhost",
        1,
        proxy_scheme="https",
        proxy_host="localhost",
        proxy_port=server.port,
        disable_certificate_validation=True,
    ) as client:
        status, data = client.send_request()

    assert status == 200
    data = data.decode("utf-8")
    data = data.split("\n")
    assert data[0].startswith("POST http://localhost:1/agent_listener/invoke_raw_method ")

    assert server.httpd.connect_host is None


def test_non_ssl_via_non_ssl_proxy(insecure_server):
    with InsecureHttpClient(
        "localhost",
        1,
        proxy_scheme="http",
        proxy_host="localhost",
        proxy_port=insecure_server.port,
    ) as client:
        status, data = client.send_request()

    assert status == 200
    data = data.decode("utf-8")
    data = data.split("\n")
    assert data[0].startswith("POST http://localhost:1/agent_listener/invoke_raw_method ")

    assert insecure_server.httpd.connect_host is None


@pytest.mark.parametrize("auth", ((None, None), ("username", None), ("username", "password")))
def test_ssl_via_non_ssl_proxy(insecure_server, auth):
    proxy_user, proxy_pass = auth
    with HttpClient(
        "localhost",
        1,
        proxy_scheme="http",
        proxy_host="localhost",
        proxy_port=insecure_server.port,
        proxy_user=proxy_user,
        proxy_pass=proxy_pass,
        disable_certificate_validation=True,
    ) as client:
        try:
            client.send_request()
        except Exception:
            pass

    try:
        if proxy_user:
            auth_expected = proxy_user
            if proxy_pass:
                auth_expected = auth_expected + ":" + proxy_pass
            auth_expected = "Basic " + base64.b64encode(auth_expected.encode("utf-8")).decode("utf-8")
            assert insecure_server.httpd.connect_headers["proxy-authorization"] == auth_expected
        else:
            assert "proxy-authorization" not in insecure_server.httpd.connect_headers
        assert insecure_server.httpd.connect_host == "localhost"
        assert insecure_server.httpd.connect_port == "1"
    finally:
        insecure_server.reset()


def test_max_payload_does_not_send(insecure_server):
    with InsecureHttpClient("localhost", insecure_server.port, max_payload_size_in_bytes=0) as client:
        status, data = client.send_request(payload=b"*")

    assert status == 413
    assert not data


@pytest.mark.parametrize(
    "method",
    (
        "preconnect",
        "connect",
        "agent_settings",
        "get_agent_commands",
        "agent_command_results",
        "metric_data",
        "analytic_event_data",
        "span_event_data",
        "error_event_data",
        "custom_event_data",
        "error_data",
        "transaction_sample_data",
        "sql_trace_data",
        "profile_data",
        "shutdown",
        "INVALID",
        None,
    ),
)
def test_developer_mode_client(method):
    params = {}
    with DeveloperModeClient("localhost", 1) as client:
        if method:
            params["method"] = method
        status, data = client.send_request(params=params)

    if not method or method == "INVALID":
        assert status == 400
    else:
        assert status == 200
        assert json.loads(data.decode("utf-8"))


def test_serverless_mode_client():
    methods = (
        "metric_data",
        "analytic_event_data",
        "span_event_data",
        "error_event_data",
        "custom_event_data",
        "error_data",
        "transaction_sample_data",
        "sql_trace_data",
    )
    with ServerlessModeClient("localhost", 1) as client:
        for method in methods:
            params = {"method": method}
            status, data = client.send_request(
                params=params,
                payload=json.dumps({"method": method}).encode("utf-8"),
            )

            assert status == 200
            assert json.loads(data.decode("utf-8"))

        # Verify that missing methods aren't captured
        status, _ = client.send_request(payload=b"{}")
        assert status == 400

        # Verify that invalid methods aren't captured
        status, _ = client.send_request(params={"method": "foo"}, payload=b"{}")
        assert status == 400

    payloads = client.finalize()
    assert len(payloads) == len(methods)
    for method in methods:
        assert payloads[method] == {"method": method}


@pytest.mark.parametrize(
    "client_cls,proxy_host,exception",
    (
        (HttpClient, "localhost", False),
        (HttpClient, None, False),
        (HttpClient, None, True),
        (ApplicationModeClient, None, True),
        (ApplicationModeClient, "localhost", True),
        (DeveloperModeClient, None, False),
        (ServerlessModeClient, None, False),
        (InsecureHttpClient, None, False),
    ),
)
def test_audit_logging(server, insecure_server, client_cls, proxy_host, exception):
    audit_log_fp = StringIO()
    params = {"method": "metric_data"}
    prefix = getattr(client_cls, "PREFIX_SCHEME", "https://")
    if exception:
        port = MockExternalHTTPServer.get_open_port()
    elif prefix == "https://":
        port = server.port
    else:
        port = insecure_server.port

    internal_metrics = CustomMetrics()

    with client_cls(
        "localhost",
        port,
        proxy_scheme="https",
        proxy_host=proxy_host,
        proxy_port=server.port if not exception else port,
        audit_log_fp=audit_log_fp,
        disable_certificate_validation=True,
    ) as client:
        with InternalTraceContext(internal_metrics):
            try:
                client.send_request(params=params)
                exc = ""
            except Exception as e:
                exc = callable_name(type(e.args[0]))

    internal_metrics = dict(internal_metrics.metrics())
    if exception and client_cls is ApplicationModeClient:
        if proxy_host:
            connection = "https-proxy"
        else:
            connection = "direct"
        assert internal_metrics == {
            "Supportability/Python/Collector/Failures": [1, 0, 0, 0, 0, 0],
            "Supportability/Python/Collector/Failures/%s" % connection: [1, 0, 0, 0, 0, 0],
            "Supportability/Python/Collector/Exception/%s" % exc: [1, 0, 0, 0, 0, 0],
        }
    else:
        assert not internal_metrics

    # Verify the audit log isn't empty
    assert audit_log_fp.tell()

    audit_log_fp.seek(0)
    audit_log_contents = audit_log_fp.read()
    assert prefix in audit_log_contents


def test_closed_connection():
    with HttpClient("localhost", MockExternalHTTPServer.get_open_port()) as client:
        with pytest.raises(NetworkInterfaceException):
            client.send_request()
