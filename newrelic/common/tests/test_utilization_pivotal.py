import os
import pytest

from newrelic.common.utilization_pivotal import PCFUtilization


@pytest.mark.parametrize('environ,expected', [
    ({}, None),
    ({'CF_INSTANCE_GUID': 'qwertyland'}, None),
    ({'CF_INSTANCE_GUID': 'a', 'CF_INSTANCE_IP': 'b', 'MEMORY_LIMIT': 'c'},
        {'cf_instance_guid': 'a', 'cf_instance_ip': 'b', 'memory_limit': 'c'})
])
def test_pivotal_environ(environ, expected, monkeypatch):
    for key, val in environ.items():
        monkeypatch.setenv(key, val)

    assert PCFUtilization.detect() == expected
