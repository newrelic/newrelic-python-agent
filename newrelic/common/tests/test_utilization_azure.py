import mock

from newrelic.packages import requests
from newrelic.common.utilization_azure import AzureUtilization

azure_success_response = (
b'{'
b'    "location": "eastus",'
b'    "name": "pythontest",'
b'    "offer": "UbuntuServer",'
b'    "osType": "Linux",'
b'    "platformFaultDomain": "0",'
b'    "platformUpdateDomain": "0",'
b'    "publisher": "Canonical",'
b'    "sku": "16.04-LTS",'
b'    "version": "16.04.201706191",'
b'    "vmId": "61481bd3-e865-4858-adb3-9e65e689e64a",'
b'    "vmSize": "Standard_DS1_v2"'
b'}')

azure_fail_response = (
b'{'
b'    "location": "eastus",'
b'}')


@mock.patch.object(requests.Session, 'get')
def test_azure_success(mock_get):
    response = requests.models.Response()
    response.status_code = 200
    response._content = azure_success_response
    mock_get.return_value = response

    d = AzureUtilization.detect()

    assert d == {'vmId': '61481bd3-e865-4858-adb3-9e65e689e64a',
            'location': 'eastus',
            'vmSize': 'Standard_DS1_v2',
            'name': 'pythontest'}


@mock.patch.object(requests.Session, 'get')
def test_azure_fail(mock_get):
    response = requests.models.Response()
    response.status_code = 200
    response._content = azure_fail_response
    mock_get.return_value = response

    d = AzureUtilization.detect()

    assert d is None
