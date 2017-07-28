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

    @classmethod
    def get_values(cls, response):
        if response is None or len(response) != 3:
            return

        values = {}
        for k, v in zip(cls.EXPECTED_KEYS, response):
            if hasattr(v, 'decode'):
                v = v.decode('utf-8')
            values[k] = v
        return values
