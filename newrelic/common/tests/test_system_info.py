from ..system_info import CpuInfo, _parse_meminfo
import os

from ..system_info import logical_cpu_count, memory_total, memory_used

def test_cpu_count():
    assert (logical_cpu_count() >= 1)

def test_memory_total():
    assert (memory_total() >= 0)

def test_memory_used():
    assert (memory_used() >= 0)

    if memory_total() > 0:
        assert (memory_used() <= memory_total())

HERE = os.path.dirname(__file__)
def test_linux_cpu():
    assert 1 == CpuInfo(HERE + '/cpuinfo_samples/1proc1coreNoHt.txt').number_of_cores()
    assert 1 == CpuInfo(HERE + '/cpuinfo_samples/1proc1coreNoHtCentos.txt').number_of_cores()
    assert 1 == CpuInfo(HERE + '/cpuinfo_samples/1proc1coreNoHtAws.txt').number_of_cores()
    assert 1 == CpuInfo(HERE + '/cpuinfo_samples/1proc1coreWithHt.txt').number_of_cores()
    assert 2 == CpuInfo(HERE + '/cpuinfo_samples/1proc2coreNoHt.txt').number_of_cores()
    assert 4 == CpuInfo(HERE + '/cpuinfo_samples/1proc4coreNoHt.txt').number_of_cores()
    assert 2 == CpuInfo(HERE + '/cpuinfo_samples/2proc1coreWithHt.txt').number_of_cores()
    assert 4 == CpuInfo(HERE + '/cpuinfo_samples/2proc2coreNoHt.txt').number_of_cores()
    assert 8 == CpuInfo(HERE + '/cpuinfo_samples/2proc4coreNoHt.txt').number_of_cores()
    assert 1 == CpuInfo(HERE + '/cpuinfo_samples/1proc1coreNoHtARMv6.txt').number_of_cores()
    assert 4 == CpuInfo(HERE + '/cpuinfo_samples/UnknownProc4coreUnknownHtVmwareCentOS.txt').number_of_cores()
    assert None == CpuInfo(HERE + '/cpuinfo_samples/non-existent.txt').number_of_cores()
    assert None == CpuInfo(HERE + '/cpuinfo_samples/malformed-file.txt').number_of_cores()

def test_linux_ram():
    assert 2012 == _parse_meminfo(HERE + '/cpuinfo_samples/meminfo.txt')
    assert None == _parse_meminfo(HERE + '/cpuinfo_samples/non-exitent.txt')
    assert None == _parse_meminfo(HERE + '/cpuinfo_samples/malformed-file.txt')


