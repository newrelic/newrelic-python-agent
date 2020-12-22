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

import inspect
import logging
import os
import ssl
import tempfile
from collections import namedtuple

import pytest

import newrelic.packages.six as six
from newrelic.common import certs, system_info
from newrelic.common.agent_http import DeveloperModeClient
from newrelic.common.encoding_utils import json_decode, serverless_payload_decode
from newrelic.common.utilization import CommonUtilization
from newrelic.core.agent_protocol import AgentProtocol, ServerlessModeProtocol
from newrelic.core.config import (
    finalize_application_settings,
    flatten_settings,
    global_settings,
)
from newrelic.core.internal_metrics import InternalTraceContext
from newrelic.core.stats_engine import CustomMetrics
from newrelic.network.exceptions import (
    DiscardDataForRequest,
    ForceAgentDisconnect,
    ForceAgentRestart,
    NetworkInterfaceException,
    RetryDataForRequest,
)

Request = namedtuple("Request", ("method", "path", "params", "headers", "payload"))


# Global constants used in tests
APP_NAME = "test_app"
IP_ADDRESS = AWS = AZURE = GCP = PCF = BOOT_ID = DOCKER = KUBERNETES = None
BROWSER_MONITORING_DEBUG = "debug"
BROWSER_MONITORING_LOADER = "loader"
CAPTURE_PARAMS = "capture_params"
DISPLAY_NAME = "display_name"
METADATA = {}
ENVIRONMENT = [["Agent Version", "test"]]
HIGH_SECURITY = True
HOST = "test_host"
LABELS = "labels"
LINKED_APPS = ["linked_app_1", "linked_app_2"]
MEMORY = 12000.0
PAYLOAD_APP_NAME = [APP_NAME] + LINKED_APPS
PAYLOAD_ID = ",".join(PAYLOAD_APP_NAME)
PID = 123
PROCESSOR_COUNT = 4
RECORD_SQL = "record_sql"
ANALYTIC_EVENT_DATA = 10000
SPAN_EVENT_DATA = 1000
CUSTOM_EVENT_DATA = 10000
ERROR_EVENT_DATA = 100


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


class HttpClientException(DeveloperModeClient):
    def send_request(
        self,
        method="POST",
        path="/agent_listener/invoke_raw_method",
        params=None,
        headers=None,
        payload=None,
    ):
        raise NetworkInterfaceException


@pytest.fixture(autouse=True)
def clear_sent_values():
    yield
    HttpClientRecorder.SENT[:] = []
    HttpClientRecorder.STATUS_CODE = None
    HttpClientRecorder.STATE = 0


@pytest.fixture(autouse=True)
def override_utilization(monkeypatch):
    global AWS, AZURE, GCP, PCF, BOOT_ID, DOCKER, KUBERNETES
    AWS = {"id": "foo", "type": "bar", "zone": "baz"}
    AZURE = {"location": "foo", "name": "bar", "vmId": "baz", "vmSize": "boo"}
    GCP = {"id": 1, "machineType": "trmntr-t1000", "name": "arnold", "zone": "abc"}
    PCF = {"cf_instance_guid": "1", "cf_instance_ip": "7", "memory_limit": "0"}
    BOOT_ID = "cca356a7d72737f645a10c122ebbe906"
    DOCKER = {"id": "foobar"}
    KUBERNETES = {"kubernetes_service_host": "10.96.0.1"}

    @classmethod
    def detect(cls):
        name = cls.__name__
        output = None
        if name.startswith("BootId"):
            output = BOOT_ID
        elif name.startswith("AWS"):
            output = AWS
        elif name.startswith("Azure"):
            output = AZURE
        elif name.startswith("GCP"):
            output = GCP
        elif name.startswith("PCF"):
            output = PCF
        elif name.startswith("Docker"):
            output = DOCKER
        elif name.startswith("Kubernetes"):
            output = KUBERNETES
        else:
            assert False, "Unknown utilization class"

        if output is Exception:
            raise Exception
        return output

    monkeypatch.setattr(CommonUtilization, "detect", detect)


@pytest.fixture(autouse=True)
def override_system_info(monkeypatch):
    global IP_ADDRESS
    IP_ADDRESS = ["127.0.0.1"]
    monkeypatch.setattr(system_info, "gethostname", lambda *args, **kwargs: HOST)
    monkeypatch.setattr(system_info, "getips", lambda *args, **kwargs: IP_ADDRESS)
    monkeypatch.setattr(
        system_info, "logical_processor_count", lambda *args, **kwargs: PROCESSOR_COUNT
    )
    monkeypatch.setattr(
        system_info, "total_physical_memory", lambda *args, **kwargs: MEMORY
    )
    monkeypatch.setattr(os, "getpid", lambda *args, **kwargs: PID)


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

    internal_metrics = CustomMetrics()
    with InternalTraceContext(internal_metrics):
        with pytest.raises(expected_exc):
            protocol.send("analytic_event_data")

    internal_metrics = dict(internal_metrics.metrics())
    if status_code == 413:
        assert internal_metrics[
            "Supportability/Python/Collector/MaxPayloadSizeLimit/analytic_event_data"
        ] == [1, 0, 0, 0, 0, 0]
    else:
        assert (
            "Supportability/Python/Collector/MaxPayloadSizeLimit/analytic_event_data"
            not in internal_metrics
        )

    assert len(HttpClientRecorder.SENT) == 1
    request = HttpClientRecorder.SENT[0]
    assert request.params["method"] == "analytic_event_data"

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == log_level
    message = caplog.records[0].getMessage()
    assert "123LICENSEKEY" not in message


def test_protocol_http_error_causes_retry():
    protocol = AgentProtocol(
        finalize_application_settings(), client_cls=HttpClientException
    )
    with pytest.raises(RetryDataForRequest):
        protocol.send("analytic_event_data")


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


def connect_payload_asserts(
    payload,
    with_aws=True,
    with_gcp=True,
    with_pcf=True,
    with_azure=True,
    with_docker=True,
    with_kubernetes=True,
):
    payload_data = payload[0]
    assert type(payload_data["agent_version"]) is type(u"")
    assert payload_data["app_name"] == PAYLOAD_APP_NAME
    assert payload_data["display_host"] == DISPLAY_NAME
    assert payload_data["environment"] == ENVIRONMENT
    assert payload_data["metadata"] == METADATA
    assert payload_data["high_security"] == HIGH_SECURITY
    assert payload_data["host"] == HOST
    assert payload_data["identifier"] == PAYLOAD_ID
    assert payload_data["labels"] == LABELS
    assert payload_data["language"] == "python"
    assert payload_data["pid"] == PID
    assert len(payload_data["security_settings"]) == 2
    assert payload_data["security_settings"]["capture_params"] == CAPTURE_PARAMS
    assert payload_data["security_settings"]["transaction_tracer"] == {
        "record_sql": RECORD_SQL
    }
    assert len(payload_data["settings"]) == 2
    assert payload_data["settings"]["browser_monitoring.loader"] == (
        BROWSER_MONITORING_LOADER
    )
    assert payload_data["settings"]["browser_monitoring.debug"] == (
        BROWSER_MONITORING_DEBUG
    )

    utilization_len = 5

    assert "full_hostname" not in payload_data["utilization"]

    if IP_ADDRESS:
        assert payload_data["utilization"]["ip_address"] == IP_ADDRESS
        utilization_len += 1
    else:
        assert "ip_address" not in payload_data["utilization"]

    utilization_len = utilization_len + any(
        [with_aws, with_pcf, with_gcp, with_azure, with_docker, with_kubernetes]
    )
    assert len(payload_data["utilization"]) == utilization_len
    assert payload_data["utilization"]["hostname"] == HOST

    assert payload_data["utilization"]["logical_processors"] == PROCESSOR_COUNT
    assert payload_data["utilization"]["metadata_version"] == 5
    assert payload_data["utilization"]["total_ram_mib"] == MEMORY
    assert payload_data["utilization"]["boot_id"] == BOOT_ID

    # Faster Event Harvest
    harvest_limits = payload_data["event_harvest_config"]["harvest_limits"]
    assert harvest_limits["analytic_event_data"] == ANALYTIC_EVENT_DATA
    assert harvest_limits["span_event_data"] == SPAN_EVENT_DATA
    assert harvest_limits["custom_event_data"] == CUSTOM_EVENT_DATA
    assert harvest_limits["error_event_data"] == ERROR_EVENT_DATA

    vendors_len = 0

    if any([with_aws, with_pcf, with_gcp, with_azure]):
        vendors_len += 1

    if with_docker:
        vendors_len += 1

    if with_kubernetes:
        vendors_len += 1

    if vendors_len:
        assert len(payload_data["utilization"]["vendors"]) == vendors_len

        # check ordering
        if with_aws:
            assert payload_data["utilization"]["vendors"]["aws"] == AWS
        elif with_pcf:
            assert payload_data["utilization"]["vendors"]["pcf"] == PCF
        elif with_gcp:
            assert payload_data["utilization"]["vendors"]["gcp"] == GCP
        elif with_azure:
            assert payload_data["utilization"]["vendors"]["azure"] == AZURE

        if with_docker:
            assert payload_data["utilization"]["vendors"]["docker"] == DOCKER

        if with_kubernetes:
            assert payload_data["utilization"]["vendors"]["kubernetes"] == KUBERNETES
    else:
        assert "vendors" not in payload_data["utilization"]


@pytest.mark.parametrize(
    "with_aws,with_pcf,with_gcp,with_azure,with_docker,with_kubernetes,with_ip",
    [
        (False, False, False, False, False, False, False),
        (False, False, False, False, False, False, True),
        (True, False, False, False, True, True, True),
        (False, True, False, False, True, True, True),
        (False, False, True, False, True, True, True),
        (False, False, False, True, True, True, True),
        (True, False, False, False, False, False, True),
        (False, True, False, False, False, False, True),
        (False, False, True, False, False, False, True),
        (False, False, False, True, False, False, True),
        (True, True, True, True, True, True, True),
        (True, True, True, True, True, False, True),
        (True, True, True, True, False, True, True),
    ],
)
def test_connect(
    with_aws, with_pcf, with_gcp, with_azure, with_docker, with_kubernetes, with_ip
):
    global AWS, AZURE, GCP, PCF, BOOT_ID, DOCKER, KUBERNETES, IP_ADDRESS
    if not with_aws:
        AWS = Exception
    if not with_pcf:
        PCF = Exception
    if not with_gcp:
        GCP = Exception
    if not with_azure:
        AZURE = Exception
    if not with_docker:
        DOCKER = Exception
    if not with_kubernetes:
        KUBERNETES = Exception
    if not with_ip:
        IP_ADDRESS = None
    settings = finalize_application_settings(
        {
            "browser_monitoring.loader": BROWSER_MONITORING_LOADER,
            "browser_monitoring.debug": BROWSER_MONITORING_DEBUG,
            "capture_params": CAPTURE_PARAMS,
            "process_host.display_name": DISPLAY_NAME,
            "transaction_tracer.record_sql": RECORD_SQL,
            "high_security": HIGH_SECURITY,
            "labels": LABELS,
            "utilization.detect_aws": with_aws,
            "utilization.detect_pcf": with_pcf,
            "utilization.detect_gcp": with_gcp,
            "utilization.detect_azure": with_azure,
            "utilization.detect_docker": with_docker,
            "utilization.detect_kubernetes": with_kubernetes,
            "event_harvest_config": {
                "harvest_limits": {
                    "analytic_event_data": ANALYTIC_EVENT_DATA,
                    "span_event_data": SPAN_EVENT_DATA,
                    "custom_event_data": CUSTOM_EVENT_DATA,
                    "error_event_data": ERROR_EVENT_DATA,
                }
            },
        }
    )
    protocol = AgentProtocol.connect(
        APP_NAME, LINKED_APPS, ENVIRONMENT, settings, client_cls=HttpClientRecorder,
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
    connect_payload_asserts(
        connect_payload,
        with_aws=with_aws,
        with_pcf=with_pcf,
        with_gcp=with_gcp,
        with_azure=with_azure,
        with_docker=with_docker,
        with_kubernetes=with_kubernetes,
    )

    # Verify agent_settings call is done with the finalized settings
    agent_settings = HttpClientRecorder.SENT[2]
    assert agent_settings.params["method"] == "agent_settings"
    agent_settings_payload = json_decode(agent_settings.payload.decode("utf-8"))
    assert len(agent_settings_payload) == 1
    agent_settings_payload = agent_settings_payload[0]

    # Finalized settings will have a non-None agent_run_id
    assert agent_settings_payload["agent_run_id"] is not None
    assert protocol.configuration.agent_run_id is not None

    # Verify that agent settings sent have converted null, containers, and
    # unserializable types to string
    assert agent_settings_payload["proxy_host"] == "None"
    assert agent_settings_payload["attributes.include"] == "[]"
    assert agent_settings_payload["feature_flag"] == str(set())
    assert isinstance(agent_settings_payload["attribute_filter"], six.string_types)

    # Verify that the connection is closed
    assert HttpClientRecorder.STATE == 0


def test_connect_metadata(monkeypatch):
    monkeypatch.setenv("NEW_RELIC_METADATA_FOOBAR", "foobar")
    monkeypatch.setenv("_NEW_RELIC_METADATA_WRONG", "wrong")
    protocol = AgentProtocol.connect(
        APP_NAME,
        LINKED_APPS,
        ENVIRONMENT,
        finalize_application_settings(),
        client_cls=HttpClientRecorder,
    )
    connect = HttpClientRecorder.SENT[1]
    assert connect.params["method"] == "connect"
    connect_payload = json_decode(connect.payload.decode("utf-8"))[0]
    assert connect_payload["metadata"] == {"NEW_RELIC_METADATA_FOOBAR": "foobar"}


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
    assert data["data"] == {"metric_data": [1, 2, 3]}

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


@pytest.mark.parametrize("ca_bundle_path", (None, "custom",))
def test_ca_bundle_path(monkeypatch, ca_bundle_path):
    # Pretend CA certificates are not available
    class DefaultVerifyPaths(object):
        cafile = None

        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(ssl, "DefaultVerifyPaths", DefaultVerifyPaths)

    settings = finalize_application_settings({"ca_bundle_path": ca_bundle_path})
    protocol = AgentProtocol(settings)
    expected = ca_bundle_path or certs.where()
    assert protocol.client._connection_kwargs["ca_certs"] == expected


def test_max_payload_size_limit():
    settings = finalize_application_settings(
        {"max_payload_size_in_bytes": 0, "port": -1}
    )
    protocol = AgentProtocol(settings, host="localhost")
    with pytest.raises(DiscardDataForRequest):
        protocol.send("metric_data")
