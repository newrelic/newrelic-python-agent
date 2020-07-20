import logging
import tempfile
from collections import namedtuple

import pytest
from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.encoding_utils import json_decode, serverless_payload_decode
from newrelic.core.agent_protocol import AgentProtocol, ServerlessModeProtocol
from newrelic.core.config import (
    finalize_application_settings,
    flatten_settings,
    global_settings,
)
from newrelic.network.exceptions import (
    DiscardDataForRequest,
    ForceAgentDisconnect,
    ForceAgentRestart,
    RetryDataForRequest,
)

Request = namedtuple("Request", ("method", "path", "params", "headers", "payload"))


class HttpClientRecorder(DeveloperModeClient):
    SENT = []
    STATUS_CODE = None
    STATE = 0

    def send_request(
        self,
        method="POST",
        path="/agent_listener/invoke_raw_method",
        params=None,
        headers=None,
        payload=None,
    ):
        request = Request(
            method=method, path=path, params=params, headers=headers, payload=payload
        )
        self.SENT.append(request)
        if self.STATUS_CODE:
            return self.STATUS_CODE, b""

        return super(HttpClientRecorder, self).send_request(
            method, path, params, headers, payload
        )

    def __enter__(self):
        HttpClientRecorder.STATE += 1

    def __exit__(self, exc, value, tb):
        HttpClientRecorder.STATE -= 1

    def close_connection(self):
        HttpClientRecorder.STATE -= 1


@pytest.fixture(autouse=True)
def clear_sent_values():
    yield
    HttpClientRecorder.SENT[:] = []
    HttpClientRecorder.STATUS_CODE = None
    HttpClientRecorder.STATE = 0


@pytest.mark.parametrize("status_code", (None, 202))
def test_send(status_code):
    HttpClientRecorder.STATUS_CODE = status_code
    settings = finalize_application_settings(
        {
            "request_headers_map": {"custom-header": u"value"},
            "agent_run_id": "RUN_TOKEN",
        }
    )
    protocol = AgentProtocol(settings, client_cls=HttpClientRecorder)
    response = protocol.send("metric_data", (1, 2, 3))
    assert response is None

    assert len(HttpClientRecorder.SENT) == 1
    request = HttpClientRecorder.SENT[0]

    assert request.method == "POST"
    assert request.path == "/agent_listener/invoke_raw_method"

    # Verify license key was there, but no way to validate the value
    request.params.pop("license_key")

    assert request.params == {
        "method": "metric_data",
        "marshal_format": "json",
        "protocol_version": AgentProtocol.VERSION,
        "run_id": "RUN_TOKEN",
    }

    assert request.headers == {
        "Content-Type": "application/json",
        "custom-header": u"value",
    }

    assert request.payload == b"[1,2,3]"

    # Verify call to finalize is None
    assert protocol.finalize() is None


@pytest.mark.parametrize(
    "status_code,expected_exc,log_level",
    (
        (400, DiscardDataForRequest, "WARNING"),
        (401, ForceAgentRestart, "ERROR"),
        (403, DiscardDataForRequest, "WARNING"),
        (404, DiscardDataForRequest, "WARNING"),
        (405, DiscardDataForRequest, "WARNING"),
        (407, DiscardDataForRequest, "WARNING"),
        (408, RetryDataForRequest, "INFO"),
        (409, ForceAgentRestart, "INFO"),
        (410, ForceAgentDisconnect, "CRITICAL"),
        (411, DiscardDataForRequest, "WARNING"),
        (413, DiscardDataForRequest, "WARNING"),
        (414, DiscardDataForRequest, "WARNING"),
        (415, DiscardDataForRequest, "WARNING"),
        (417, DiscardDataForRequest, "WARNING"),
        (429, RetryDataForRequest, "WARNING"),
        (431, DiscardDataForRequest, "WARNING"),
        (500, RetryDataForRequest, "WARNING"),
        (503, RetryDataForRequest, "WARNING"),
        (800, DiscardDataForRequest, "WARNING"),
    ),
)
def test_status_code_exceptions(status_code, expected_exc, log_level, caplog):
    caplog.set_level(logging.INFO)
    HttpClientRecorder.STATUS_CODE = status_code
    settings = finalize_application_settings({"license_key": "123LICENSEKEY",})
    protocol = AgentProtocol(settings, client_cls=HttpClientRecorder)
    with pytest.raises(expected_exc):
        protocol.send("analytic_event_data")

    assert len(HttpClientRecorder.SENT) == 1
    request = HttpClientRecorder.SENT[0]
    assert request.params["method"] == "analytic_event_data"

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == log_level
    message = caplog.records[0].getMessage()
    assert "123LICENSEKEY" not in message


def test_protocol_context_manager():
    protocol = AgentProtocol(
        finalize_application_settings(), client_cls=HttpClientRecorder
    )
    with protocol:
        assert HttpClientRecorder.STATE == 1

    assert HttpClientRecorder.STATE == 0


def test_close_connection():
    protocol = AgentProtocol(
        finalize_application_settings(), client_cls=HttpClientRecorder
    )
    protocol.close_connection()
    assert HttpClientRecorder.STATE == -1


def test_connect():
    settings = global_settings()
    protocol = AgentProtocol.connect(
        "testapp",
        ["foo"],
        [("Agent Version", "test")],
        settings,
        client_cls=HttpClientRecorder,
    )

    # verify there are exactly 3 calls to HttpClientRecorder
    assert len(HttpClientRecorder.SENT) == 3

    # Verify preconnect call
    preconnect = HttpClientRecorder.SENT[0]
    assert preconnect.params["method"] == "preconnect"
    assert preconnect.payload == b"[]"

    # Verify connect call
    connect = HttpClientRecorder.SENT[1]
    assert connect.params["method"] == "connect"
    connect_payload = json_decode(connect.payload.decode("utf-8"))

    assert len(connect_payload) == 1
    connect_payload = connect_payload[0]

    # Verify inputs to connect are sent in the payload
    assert connect_payload["language"] == "python"
    assert connect_payload["app_name"] == ["testapp", "foo"]
    assert connect_payload["identifier"] == "testapp,foo"
    assert connect_payload["environment"] == [["Agent Version", "test"]]

    # Verify agent_settings call is done with the finalized settings
    agent_settings = HttpClientRecorder.SENT[2]
    assert agent_settings.params["method"] == "agent_settings"
    agent_settings_payload = json_decode(agent_settings.payload.decode("utf-8"))
    assert len(agent_settings_payload) == 1
    agent_settings_payload = agent_settings_payload[0]

    # Finalized settings will have a non-None agent_run_id
    assert agent_settings_payload["agent_run_id"] is not None
    assert protocol.configuration.agent_run_id is not None

    # Verify that the connection is closed
    assert HttpClientRecorder.STATE == 0


def test_serverless_protocol_connect():
    settings = global_settings()
    protocol = ServerlessModeProtocol.connect(
        "testapp",
        ["foo"],
        [("Agent Version", "test")],
        settings,
        client_cls=HttpClientRecorder,
    )

    # No client calls should be made
    assert len(HttpClientRecorder.SENT) == 0

    # cross application tracing must be disabled
    assert not protocol.configuration.cross_application_tracer.enabled


def test_serverless_protocol_finalize(capsys):
    protocol = ServerlessModeProtocol(
        finalize_application_settings(
            {"aws_lambda_metadata": {"foo": "bar", "agent_version": "x"}}
        )
    )
    response = protocol.send("metric_data", (1, 2, 3))
    assert response is None

    payload = protocol.finalize()
    captured = capsys.readouterr()
    assert captured.out.rstrip("\n") == payload

    payload = json_decode(payload)
    assert payload[:2] == [1, "NR_LAMBDA_MONITORING"]

    data = serverless_payload_decode(payload[2])
    assert data["data"] == {"metric_data": "[1,2,3]"}

    assert data["metadata"]["foo"] == "bar"
    assert data["metadata"]["agent_version"] != "x"


def test_audit_logging():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"*\n")

    settings = finalize_application_settings({"audit_log_file": f.name})
    protocol = AgentProtocol(settings, client_cls=HttpClientRecorder)
    protocol.send("preconnect")

    with open(f.name) as f:
        audit_log_contents = f.read()

    assert audit_log_contents.startswith("*\n")
    assert len(audit_log_contents) > 2
