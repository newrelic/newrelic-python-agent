# Requirements: Capture the number of physical cores, number of logical
# processors and total physical memory. When a value can't be reliably obtained
# return 'null'
#
# Cores:
#        Processor               Physical    Logical
# 1 processor 1 core No HT          1           1
# 1 processor 2 core No HT          2           2
# 2 processor 2 core No HT          4           8
# 1 processor 1 core with HT        1           2
# 1 processor 2 core with HT        2           4
# 2 processor 2 core with HT        4           8
#
# Linux - Parse a file
# CPU : Parse /proc/cpuinfo
# MEM : Parse /proc/meminfo
#
# OS X - Run a shell command
# CPU : /usr/sbin/sysctl -n hw.physicalcpu
# MEM : /usr/sbin/sysctl -n hw.memsize
#
# JSON Format for 'connect'
# ["Logical Processors",8],["Physical Processors",4],["Total Physical Memory (MB)",8192.0]
#

import os
from subprocess import Popen, PIPE
import multiprocessing

LINUX_CPU = '/proc/cpuinfo'
LINUX_MEM = '/proc/meminfo'

DARWIN_CPU = '/usr/sbin/sysctl'
DARWIN_MEM = '/usr/sbin/sysctl'

def _extract_shell_results(*command):
    """
    Run a shell command and cast the output to an integer. Returns None on
    failure.
    """
    result = None
    output, err = Popen(command, stdout=PIPE, stderr=PIPE).communicate()
    if not err:
        try:
            result = int(output)
        except ValueError:
            pass
    return result

class CpuInfo(object):
    """
    Handles the parsing of a cpuinfo file to obtain the number of physical
    cores.
    """
    def __init__(self, filename=None):
        self.filename = filename or '/proc/cpuinfo'
        self.processors = 0
        self.physical_cores = {}
        self._reset()
        self._parse_file()

    def _reset(self):
        self.physical_id = None
        self.cores = None

    def _parse_file(self):
        # A line that starts with 'processor' marks the beginning of a
        # section.
        #
        # Multi-core processors will have a 'processor' section for each core.
        # Thereis usually a 'physical id' field and a 'cpu cores' field as
        # well.  The 'physical id' field in each 'processor' section will have
        # the same value for all cores. The 'cpu cores' field for each
        # 'processor' section will provide the total number of cores for that
        # physical processor.

        try:
            for original_line in open(self.filename):
                line = original_line.lower()
                if line.startswith('processor'):
                    self.processors += 1
                    if (self.cores and self.physical_id):
                        self.physical_cores[self.physical_id] = self.cores
                        self._reset()
                elif line.startswith('physical id'):
                    self.physical_id = line.split(':')[1]
                elif line.startswith('cpu cores'):
                    self.cores = int(line.split(':')[1])
        except:
            pass

    def number_of_cores(self):
        return sum(self.physical_cores.values()) or self.processors or None

def _parse_meminfo(meminfo):
    # Parse /proc/meminfo for 'memtotal'. The value is 'meminfo' file is in
    # MB. Return the result in MB.

    normalizer = {'kb': 1024, 'mb': 1}
    try:
        for line in open(meminfo):
            if line.lower().startswith('memtotal'):
                mem = line.split(":")[1]
                value, units = mem.split()
                return int(value)/normalizer[units.lower()]
    except:
        return None

def cpu_count():
    """
    Return a tuple (physical_cores, logical_cores)
    """
    if os.path.isfile(LINUX_CPU):
        cpu_info = CpuInfo(LINUX_CPU)
        physical_cores = cpu_info.number_of_cores()
    elif os.path.isfile(DARWIN_CPU):
        command = (DARWIN_CPU, "-n", "hw.physicalcpu")
        physical_cores = _extract_shell_results(*command)

    logical_cores = multiprocessing.cpu_count()

    return (physical_cores, logical_cores)

def total_ram():
    """
    Return the size of RAM in MB.
    """
    ram = None
    if os.path.isfile(DARWIN_MEM):
        command = (DARWIN_CPU, "-n", "hw.memsize")
        try:
            ram = _extract_shell_results(*command)/(1024 * 1024)
        except TypeError:
            pass
    elif os.path.isfile(LINUX_MEM):
        ram = _parse_meminfo(LINUX_MEM)

    return ram
