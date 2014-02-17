import os
import pytest

from ..system_info import (logical_processor_count, physical_processor_count,
        total_physical_memory, physical_memory_used,
        _linux_physical_processor_count, _linux_total_physical_memory)

def test_logical_processor_count():
    assert logical_processor_count() >= 1

def test_physical_processor_count():
    count = physical_processor_count()

    assert count is None or count >= 0

def test_total_physical_memory():
    assert total_physical_memory() >= 0

def test_physical_memory_used():
    assert physical_memory_used() >= 0

    if total_physical_memory() > 0:
        assert physical_memory_used() <= total_physical_memory()

@pytest.mark.parametrize('filename,expected', [
    ('1proc1coreNoHt.txt', 1),
    ('1proc1coreNoHtCentos.txt', 1),
    ('1proc1coreNoHtAws.txt', 1),
    ('1proc1coreWithHt.txt', 1),
    ('1proc2coreNoHt.txt', 2),
    ('1proc4coreNoHt.txt', 4),
    ('2proc1coreWithHt.txt', 2),
    ('2proc2coreNoHt.txt', 4),
    ('2proc4coreNoHt.txt', 8),
    ('1proc1coreNoHtARMv6.txt', 1),
    ('UnknownProc4coreUnknownHtVmwareCentOS.txt', 4),
    ('malformed-file.txt', None),
    ('non-existant-file.txt', None)])
def test_linux_physical_processor_count(filename, expected):
    here = os.path.dirname(__file__)
    path = os.path.join(here, 'system_info', filename)

    count = _linux_physical_processor_count(path)
    assert count == expected

@pytest.mark.parametrize('filename,expected', [
    ('meminfo.txt', 2061052/1024.0),
    ('malformed-file', None),
    ('non-existant-file.txt', None)])
def test_linux_total_physical_memory(filename, expected):
    here = os.path.dirname(__file__)
    path = os.path.join(here, 'system_info', filename)

    value = _linux_total_physical_memory(path)
    assert value == expected
