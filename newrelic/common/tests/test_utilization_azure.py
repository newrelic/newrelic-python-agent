import functools

from newrelic.common.utilization import AzureUtilization
from newrelic.common.tests.test_utilization_common import http_client_cls

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


def test_azure_success():
    AzureUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=azure_success_response,
                                            utilization_cls=AzureUtilization)

    d = AzureUtilization.detect()

    assert d == {'vmId': '61481bd3-e865-4858-adb3-9e65e689e64a',
            'location': 'eastus',
            'vmSize': 'Standard_DS1_v2',
            'name': 'pythontest'}

    assert not AzureUtilization.CLIENT_CLS.FAIL



def test_azure_fail():
    AzureUtilization.CLIENT_CLS = http_client_cls(status=200,
                                            data=azure_fail_response,
                                            utilization_cls=AzureUtilization)

    d = AzureUtilization.detect()

    assert d is None
