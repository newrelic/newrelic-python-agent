from newrelic.common.utilization_common import CommonUtilization


class AzureUtilization(CommonUtilization):
    METADATA_URL = ('http://169.254.169.254'
            '/metadata/instance/compute?api-version=2017-03-01')
    EXPECTED_KEYS = ['location', 'name', 'vmId', 'vmSize']
    HEADERS = {'Metadata': 'true'}
    VENDOR_NAME = 'azure'
