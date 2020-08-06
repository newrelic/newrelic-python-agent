import json
import functools

from newrelic.common.utilization import (CommonUtilization,
        GCPUtilization)
from newrelic.common.tests.test_utilization_common import http_client_cls


_mock_response_data = b"""{
        "cpuPlatform": "Intel Haswell",
        "hostname": "meow-bot.c.geometric-watch-90521.internal",
        "machineType": "projects/123456/machineTypes/f1-micro",
        "description": "",
        "zone": "projects/123456/zones/us-central1-b",
        "maintenanceEvent": "NONE",
        "image": "",
        "disks": [{"deviceName": "meow-bot", "type": "PERSISTENT",
        "mode": "READ_WRITE", "index": 0}],
        "scheduling": {"automaticRestart": "TRUE", "preemptible":
        "FALSE", "onHostMaintenance": "MIGRATE"},
        "virtualClock": {"driftToken": "0"},
        "licenses": [{"id": "987654"}],
        "attributes": {},
        "serviceAccounts": {"default": {"scopes":
        ["https://www.googleapis.com/auth/devstorage.read_only",
        "https://www.googleapis.com/auth/logging.write"],
        "email": "123456-compute@developer.gserviceaccount.com",
        "aliases": ["default"]},
        "123456-compute@developer.gserviceaccount.com": {"scopes":
        ["https://www.googleapis.com/auth/devstorage.read_only",
        "https://www.googleapis.com/auth/logging.write"],
        "email": "123456-compute@developer.gserviceaccount.com",
        "aliases": ["default"]}},
        "networkInterfaces": [{"network":
        "projects/123456/networks/default", "ipAliases": [],
        "ip": "1.2.3.4", "mac": "42:01:0a:f0:8a:b6",
        "accessConfigs": [{"externalIp": "9.8.7.6", "type":
        "ONE_TO_ONE_NAT"}], "forwardedIps": []}],
        "id": 1234567890123456,
        "tags": ["http-server", "https-server"],
        "name": "meow-bot"}"""


def test_gcp_vendor_info():
    gcp = GCPUtilization()
    assert isinstance(gcp, GCPUtilization)
    assert gcp.VENDOR_NAME == 'gcp'


def test_fetch():
    GCPUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=b'{"data": "check"}',
                                            utilization_cls=GCPUtilization)
    response = b'{"data": "check"}'
    resp = GCPUtilization().fetch()

    assert resp == response

    assert not GCPUtilization.CLIENT_CLS.FAIL


def test_normalize_instance_id():
    data = 1234567890123456
    assert GCPUtilization.normalize('id', data) == "1234567890123456"


def test_normalize_machine_type():
    data = "projects/123456/machineTypes/f1-micro"
    assert GCPUtilization.normalize('machineType', data) == "f1-micro"


def test_normalize_name():
    data = "meow-bot"
    assert GCPUtilization.normalize('name', data) == "meow-bot"


def test_normalize_zone():
    data = "projects/123456/zones/us-central1-b"
    assert GCPUtilization.normalize('zone', data) == "us-central1-b"


def test_normalize_nonetype():
    data = None
    assert GCPUtilization.normalize('O--nn', data) is None


def test_normalize_different_key():
    data = "wruff"
    assert GCPUtilization.normalize('O--nn', data) == \
            CommonUtilization.normalize('O--nn', data)

    assert not GCPUtilization.CLIENT_CLS.FAIL


def test_sanitize():
    gcp = GCPUtilization()
    assert gcp.sanitize(json.loads(_mock_response_data.decode('utf-8'))) == \
            {'id': '1234567890123456', 'name': 'meow-bot',
            'machineType': 'f1-micro', 'zone': 'us-central1-b'}

    assert not GCPUtilization.CLIENT_CLS.FAIL


def test_detect_good_response():
    GCPUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=_mock_response_data,
                                            utilization_cls=GCPUtilization)

    gcp = GCPUtilization()
    assert gcp.detect() == {'id': '1234567890123456', 'name': 'meow-bot',
            'machineType': 'f1-micro', 'zone': 'us-central1-b'}

    assert not GCPUtilization.CLIENT_CLS.FAIL


def test_detect_error_status():
    GCPUtilization.CLIENT_CLS = http_client_cls(status=500,
                                            data=None,
                                            utilization_cls=GCPUtilization)

    gcp = GCPUtilization()
    assert gcp.detect() is None


def test_detect_invalid_response():
    GCPUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=b"{'id': 1234567,'name': 'meow-bot'}",
                                            utilization_cls=GCPUtilization)

    gcp = GCPUtilization()
    assert gcp.detect() is None
