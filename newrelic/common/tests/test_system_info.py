from ..system_info import CpuInfo, _parse_meminfo

def test_linux_cpu():
    assert 1 == CpuInfo('cpuinfo_samples/1proc1coreNoHt.txt').number_of_cores()
    assert 1 == CpuInfo('cpuinfo_samples/1proc1coreNoHtCentos.txt').number_of_cores()
    assert 1 == CpuInfo('cpuinfo_samples/1proc1coreNoHtAws.txt').number_of_cores()
    assert 1 == CpuInfo('cpuinfo_samples/1proc1coreWithHt.txt').number_of_cores()
    assert 2 == CpuInfo('cpuinfo_samples/1proc2coreNoHt.txt').number_of_cores()
    assert 4 == CpuInfo('cpuinfo_samples/1proc4coreNoHt.txt').number_of_cores()
    assert 2 == CpuInfo('cpuinfo_samples/2proc1coreWithHt.txt').number_of_cores()
    assert 4 == CpuInfo('cpuinfo_samples/2proc2coreNoHt.txt').number_of_cores()
    assert 8 == CpuInfo('cpuinfo_samples/2proc4coreNoHt.txt').number_of_cores()
    assert 1 == CpuInfo('cpuinfo_samples/1proc1coreNoHtARMv6.txt').number_of_cores()
    assert 4 == CpuInfo('cpuinfo_samples/UnknownProc4coreUnknownHtVmwareCentOS.txt').number_of_cores()
    assert None == CpuInfo('cpuinfo_samples/non-existent.txt').number_of_cores()
    assert None == CpuInfo('cpuinfo_samples/malformed-file.txt').number_of_cores()

def test_linux_ram():
    assert 2012 == _parse_meminfo('cpuinfo_samples/meminfo.txt')
    assert None == _parse_meminfo('cpuinfo_samples/non-exitent.txt')
    assert None == _parse_meminfo('cpuinfo_samples/malformed-file.txt')
