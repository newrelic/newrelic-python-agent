import os
import pytest

from newrelic.common.system_info import (logical_processor_count,
        physical_processor_count, total_physical_memory, physical_memory_used,
        _linux_physical_processor_count, _linux_total_physical_memory)


def test_logical_processor_count():
    assert logical_processor_count() >= 1


def test_physical_processor_count():
    processors_count, cores_count = physical_processor_count()
    assert processors_count is None or processors_count >= 0
    assert cores_count is None or cores_count >= 0


def test_total_physical_memory():
    assert total_physical_memory() >= 0


def test_physical_memory_used():
    assert physical_memory_used() >= 0

    if total_physical_memory() > 0:
        assert physical_memory_used() <= total_physical_memory()


@pytest.mark.parametrize('filename,expected', [
    ('1pack_1core_1logical.txt', (1, 1)),
    ('1pack_1core_2logical.txt', (1, 1)),
    ('1pack_2core_2logical.txt', (1, 2)),
    ('1pack_4core_4logical.txt', (1, 4)),
    ('2pack_12core_24logical.txt', (2, 12)),
    ('2pack_20core_40logical.txt', (2, 20)),
    ('2pack_2core_2logical.txt', (2, 2)),
    ('2pack_2core_4logical.txt', (2, 2)),
    ('2pack_4core_4logical.txt', (2, 4)),
    ('4pack_4core_4logical.txt', (4, 4)),
    ('8pack_8core_8logical.txt', (8, 8)),
    ('Xpack_Xcore_2logical.txt', (None, None)),
    ('malformed_file.txt', (None, None)),
    ('non-existant-file.txt', (None, None))])
def test_linux_physical_processor_count(filename, expected):
    here = os.path.dirname(__file__)
    path = os.path.join(here, 'fixtures', 'proc_cpuinfo', filename)

    result = _linux_physical_processor_count(path)
    assert result == expected


@pytest.mark.parametrize('filename,expected', [
    ('meminfo_4096MB.txt', 4194304 / 1024.0),
    ('malformed-file', None),
    ('non-existant-file.txt', None)])
def test_linux_total_physical_memory(filename, expected):
    here = os.path.dirname(__file__)
    path = os.path.join(here, 'fixtures', 'proc_meminfo', filename)

    value = _linux_total_physical_memory(path)
    assert value == expected
