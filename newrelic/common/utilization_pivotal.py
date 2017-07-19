import os

from newrelic.common.utilization_common import CommonUtilization


class PCFUtilization(CommonUtilization):
    EXPECTED_KEYS = ('cf_instance_guid', 'cf_instance_ip', 'memory_limit')
    VENDOR_NAME = 'pcf'

    @classmethod
    def fetch(cls):
        return {
            'cf_instance_guid': os.environ.get('CF_INSTANCE_GUID'),
            'cf_instance_ip': os.environ.get('CF_INSTANCE_IP'),
            'memory_limit': os.environ.get('MEMORY_LIMIT'),
        }

    @classmethod
    def get_values(cls, response):
        return response
