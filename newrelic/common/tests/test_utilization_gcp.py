import json
import mock

from newrelic.common.utilization_common import CommonUtilization
from newrelic.common.utilization_gcp import GCPUtilization
from newrelic.packages import requests


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

_mock_exception_data = """
        <!DOCTYPE html>
        <html lang=en>
          <meta charset=utf-8>
            <meta name=viewport content="initial-scale=1, minimum-scale=1,
            width=device-width">
              <title>Error 403 (Forbidden)!!1</title>
                <style>
                    *{margin:0;padding:0}html,code{font:15px/22px arial,
                    sans-serif}html{background:#fff;color:#222;padding:15px}
                    body{margin:7% auto 0;max-width:390px;min-height:180px;
                    padding:30px 0 15px}* > body{background:url(
                    //www.google.com/images/errors/robot.png) 100% 5px
                    no-repeat;padding-right:205px}p{margin:11px 0
                    22px;overflow:hidden}ins{color:#777;text-decoration:none}a
                    img{border:0}@media screen and (max-width:772px){body{
                    background:none;margin-top:0;max-width:none;padding-right:
                    0}}#logo{background:url(//www.google.com/images/branding/
                    googlelogo/1x/googlelogo_color_150x54dp.png) no-repeat;
                    margin-left:-5px}@media only screen and (min-resolution:
                    192dpi){#logo{background:url(//www.google.com/images/
                    branding/googlelogo/2x/googlelogo_color_150x54dp.png)
                    no-repeat 0% 0%/100% 100%;-moz-border-image:url(
                    //www.google.com/images/branding/googlelogo/2x/
                    googlelogo_color_150x54dp.png) 0}}@media only screen and
                    (-webkit-min-device-pixel-ratio:2){#logo{background:url(
                    //www.google.com/images/branding/googlelogo/2x/
                    googlelogo_color_150x54dp.png) no-repeat;-webkit-
                    background-size:100% 100%}}#logo{display:inline-block;
                    height:54px;width:150px}
                </style>
                <a href=//www.google.com/><span id=logo aria-label=Google>
                </span></a>
                <p><b>403.</b> <ins>That\u2019s an error.</ins>
                <p>Your client does not have permission to get URL<code>
                /computeMetadata/v1/instance/?recursive=true</code>
                from this server. Missing Metadata-Flavor:Google header.
                <ins>That\u2019s all we know.</ins>
"""


def test_gcp_vendor_info():
    gcp = GCPUtilization()
    assert isinstance(gcp, GCPUtilization)
    assert gcp.VENDOR_NAME == 'gcp'


@mock.patch.object(requests.Session, 'get')
def test_fetch(get_mock):
    response_mock = mock.Mock()

    get_mock.return_value = response_mock

    gcp = GCPUtilization()
    assert gcp.fetch() == response_mock

    get_mock.assert_called_with(GCPUtilization.METADATA_URL,
            headers={'Metadata-Flavor': 'Google'},
            timeout=GCPUtilization.TIMEOUT)
    response_mock.raise_for_status.assert_called_with()


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


def test_sanitize():
    gcp = GCPUtilization()
    assert gcp.sanitize(json.loads(_mock_response_data.decode('utf-8'))) == \
            {'id': '1234567890123456', 'name': 'meow-bot',
            'machineType': 'f1-micro', 'zone': 'us-central1-b'}


@mock.patch.object(requests.Session, 'get')
def test_detect_good_response(get_mock):
    response = requests.models.Response()
    response.status_code = 200
    response._content = _mock_response_data
    get_mock.return_value = response

    gcp = GCPUtilization()
    assert gcp.detect() == {'id': '1234567890123456', 'name': 'meow-bot',
            'machineType': 'f1-micro', 'zone': 'us-central1-b'}
    get_mock.assert_called_with(GCPUtilization.METADATA_URL,
            headers={'Metadata-Flavor': 'Google'},
            timeout=GCPUtilization.TIMEOUT)
    assert len(get_mock.call_args_list) == 1  # Should be called once.


@mock.patch.object(requests.Session, 'get')
def test_detect_bad_response(get_mock):
    response = requests.models.Response()
    response.status_code = 403
    response._content = _mock_exception_data
    get_mock.return_value = response

    gcp = GCPUtilization()
    assert gcp.detect() is None


@mock.patch.object(requests.Session, 'get')
def test_detect_ugly_response(get_mock):
    response = requests.models.Response()
    response.status_code = 200
    response._content = b"{'id': 123456789, 'name': 'meow-bot'}"

    get_mock.return_value = response

    gcp = GCPUtilization()
    assert gcp.detect() is None
