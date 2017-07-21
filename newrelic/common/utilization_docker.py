import string
import re
from newrelic.common.utilization_common import CommonUtilization

match_exp = r'([0-9a-f]{64,})'
DOCKER_RE = re.compile(match_exp)


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

        value = contents.split('/')[-1]
        match = DOCKER_RE.search(value)
        if match:
            value = match.group(0)
            return {'id': value}

    @classmethod
    def valid_chars(cls, data):
        if data is None:
            return False

        hex_digits = set(string.hexdigits)

        valid = all((c in hex_digits for c in data))
        if valid:
            return True

        return False

    @classmethod
    def valid_length(cls, data):
        if data is None:
            return False

        # Must be exactly 64 characters
        valid = len(data) == 64
        if valid:
            return True

        return False
