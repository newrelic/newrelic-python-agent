import string
from newrelic.common.utilization_common import CommonUtilization


class DockerUtilization(CommonUtilization):
    VENDOR_NAME = 'docker'
    EXPECTED_KEYS = ('id',)
    METADATA_FILE = '/proc/self/cgroup'

    @classmethod
    def fetch(cls):
        try:
            with open(cls.METADATA_FILE, 'rb') as f:
                for line in f:
                    stripped = line.decode('utf-8').strip()
                    cgroup = stripped.split(':')
                    if len(cgroup) != 3:
                        continue
                    subsystems = cgroup[1].split(',')
                    if 'cpu' in subsystems:
                        return cgroup[2]
        except:
            # There are all sorts of exceptions that can occur here
            # (i.e. permissions, non-existent file, etc)
            pass

    @classmethod
    def get_values(cls, contents):
        if contents is None:
            return

        # parse the line
        if '/' not in contents:
            return

        value = contents.split('/')[-1]

        return {'id': value}

    @classmethod
    def valid_chars(cls, data):
        if data is None:
            return False

        hex_digits = set(string.hexdigits)

        valid = all((c in hex_digits for c in data))
        if valid:
            return True

        cls.record_error(cls.METADATA_FILE, data)
        return False

    @classmethod
    def valid_length(cls, data):
        if data is None:
            return False

        # Must be exactly 64 characters
        valid = len(data) == 64
        if valid:
            return True

        cls.record_error(cls.METADATA_FILE, data)
        return False
