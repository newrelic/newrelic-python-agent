import os

from newrelic.common.utilization_common import CommonUtilization


class PCFUtilization(CommonUtilization):
    EXPECTED_KEYS = ('cf_instance_guid', 'cf_instance_ip', 'memory_limit')
    VENDOR_NAME = 'pcf'

    @staticmethod
    def fetch():
        cf_instance_guid = os.environ.get('CF_INSTANCE_GUID')
        cf_instance_ip = os.environ.get('CF_INSTANCE_IP')
        memory_limit = os.environ.get('MEMORY_LIMIT')
        pcf_vars = (cf_instance_guid, cf_instance_ip, memory_limit)
        if all(pcf_vars):
            return pcf_vars

    @staticmethod
    def get_values(response):
        if response is not None and len(response) == 3:
            return {
                'cf_instance_guid': response[0],
                'cf_instance_ip': response[1],
                'memory_limit': response[2],
            }
