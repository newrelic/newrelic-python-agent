"""This module implements functions for querying properties of the operating
system or for the specific process the code is running in.

"""

import logging
import multiprocessing
import os
import re
import socket
import subprocess
import sys
import threading

from newrelic.core.internal_metrics import internal_metric

try:
    from subprocess import check_output as _execute_program
except ImportError:
    def _execute_program(*popenargs, **kwargs):
        # Replicates check_output() implementation from Python 2.7+.
        # Should only be used for Python 2.6.

        if 'stdout' in kwargs:
            raise ValueError(
                    'stdout argument not allowed, it will be overridden.')
        process = subprocess.Popen(stdout=subprocess.PIPE,
                *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd, output=output)
        return output

try:
    import resource
except ImportError:
    pass

_logger = logging.getLogger(__name__)

LOCALHOST_EQUIVALENTS = set([
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '0:0:0:0:0:0:0:0',
    '0:0:0:0:0:0:0:1',
    '::1',
    '::',
])


def logical_processor_count():
    """Returns the number of logical processors in the system.

    """

    # The multiprocessing module provides support for Windows,
    # BSD systems (including MacOS X) and systems which support
    # the POSIX API for querying the number of CPUs.

    try:
        return multiprocessing.cpu_count()
    except NotImplementedError:
        pass

    # For Jython, we need to query the Java runtime environment.

    try:
        from java.lang import Runtime
        runtime = Runtime.getRuntime()
        res = runtime.availableProcessors()
        if res > 0:
            return res
    except ImportError:
        pass

    # Assuming that Solaris will support POSIX API for querying
    # the number of CPUs. Just in case though, work it out by
    # looking at the devices corresponding to the available CPUs.

    try:
        pseudoDevices = os.listdir('/devices/pseudo/')
        expr = re.compile('^cpuid@[0-9]+$')

        res = 0
        for pd in pseudoDevices:
            if expr.match(pd) is not None:
                res += 1

        if res > 0:
            return res
    except OSError:
        pass

    # Fallback to assuming only a single CPU.

    return 1


def _linux_physical_processor_count(filename=None):
    # For Linux we can use information from '/proc/cpuinfo.

    # A line in the file that starts with 'processor' marks the
    # beginning of a section.
    #
    # Multi-core processors will have a 'processor' section for each
    # core. There is usually a 'physical id' field and a 'cpu cores'
    # field as well.  The 'physical id' field in each 'processor'
    # section will have the same value for all cores in a physical
    # processor. The 'cpu cores' field for each 'processor' section will
    # provide the total number of cores for that physical processor.
    # The 'cpu cores' field is duplicated, so only remember the last

    filename = filename or '/proc/cpuinfo'

    processors = 0
    physical_processors = {}

    try:
        with open(filename, 'r') as fp:
            processor_id = None
            cores = None

            for line in fp:
                try:
                    key, value = line.split(':')
                    key = key.lower().strip()
                    value = value.strip()

                except ValueError:
                    continue

                if key == 'processor':
                    processors += 1

                    # If this is not the first processor section
                    # and prior sections specified a physical ID
                    # and number of cores, we want to remember
                    # the number of cores corresponding to that
                    # physical core. Note that we may see details
                    # for the same phyiscal ID more than one and
                    # thus we only end up remember the number of
                    # cores from the last one we see.

                    if cores and processor_id:
                        physical_processors[processor_id] = cores

                        processor_id = None
                        cores = None

                elif key == 'physical id':
                    processor_id = value

                elif key == 'cpu cores':
                    cores = int(value)

        # When we have reached the end of the file, we now need to save
        # away the number of cores for the physical ID we saw in the
        # last processor section.

        if cores and processor_id:
            physical_processors[processor_id] = cores

    except Exception:
        pass

    num_physical_processors = len(physical_processors) or (processors
                                        if processors == 1 else None)
    num_physical_cores = sum(physical_processors.values()) or (processors
                                        if processors == 1 else None)

    return (num_physical_processors, num_physical_cores)


def _darwin_physical_processor_count():
    # For MacOS X we can use sysctl.

    physical_processor_cmd = ['/usr/sbin/sysctl', '-n', 'hw.packages']

    try:
        num_physical_processors = int(_execute_program(physical_processor_cmd,
            stderr=subprocess.PIPE))
    except (subprocess.CalledProcessError, ValueError):
        num_physical_processors = None

    physical_core_cmd = ['/usr/sbin/sysctl', '-n', 'hw.physicalcpu']

    try:
        num_physical_cores = int(_execute_program(physical_core_cmd,
            stderr=subprocess.PIPE))
    except (subprocess.CalledProcessError, ValueError):
        num_physical_cores = None

    return (num_physical_processors, num_physical_cores)


def physical_processor_count():
    """Returns the number of physical processors and the number of physical
    cores in the system as a tuple. One or both values may be None, if a value
    cannot be determined.

    """

    if sys.platform.startswith('linux'):
        return _linux_physical_processor_count()
    elif sys.platform == 'darwin':
        return _darwin_physical_processor_count()

    return (None, None)


def _linux_total_physical_memory(filename=None):
    # For Linux we can use information from /proc/meminfo. Although the
    # units is given in the file, it is always in kilobytes so we do not
    # need to accomodate any other unit types beside 'kB'.

    filename = filename or '/proc/meminfo'

    try:
        parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')

        with open(filename, 'r') as fp:
            for line in fp.readlines():
                match = parser.match(line)
                if not match:
                    continue
                key, value = match.groups(['key', 'value'])
                if key == 'MemTotal':
                    memory_bytes = float(value) * 1024
                    return memory_bytes / (1024 * 1024)

    except Exception:
        pass


def _darwin_total_physical_memory():
    # For MacOS X we can use sysctl. The value queried from sysctl is
    # always bytes.

    command = ['/usr/sbin/sysctl', '-n', 'hw.memsize']

    try:
        return float(_execute_program(command,
                stderr=subprocess.PIPE)) / (1024 * 1024)
    except subprocess.CalledProcessError:
        pass
    except ValueError:
        pass


def total_physical_memory():
    """Returns the total physical memory available in the system. Returns
    None if the value cannot be calculated.

    """

    if sys.platform.startswith('linux'):
        return _linux_total_physical_memory()
    elif sys.platform == 'darwin':
        return _darwin_total_physical_memory()


def _linux_physical_memory_used(filename=None):
    # For Linux we can use information from the proc filesystem. We use
    # '/proc/statm' as it easier to parse than '/proc/status' file. The
    # value queried from the file is always in bytes.
    #
    #   /proc/[number]/statm
    #          Provides information about memory usage, measured
    #          in pages. The columns are:
    #
    #              size       total program size
    #                         (same as VmSize in /proc/[number]/status)
    #              resident   resident set size
    #                         (same as VmRSS in /proc/[number]/status)
    #              share      shared pages (from shared mappings)
    #              text       text (code)
    #              lib        library (unused in Linux 2.6)
    #              data       data + stack
    #              dt         dirty pages (unused in Linux 2.6)

    filename = filename or '/proc/%d/statm' % os.getpid()

    try:
        with open(filename, 'r') as fp:
            rss_pages = float(fp.read().split()[1])
            memory_bytes = rss_pages * resource.getpagesize()
            return memory_bytes / (1024 * 1024)

    except Exception:
        return 0


def physical_memory_used():
    """Returns the amount of physical memory used in MBs. Returns 0 if
    the value cannot be calculated.

    """

    # A value of 0 is returned by default rather than None as this value
    # can be used in metrics. As such has traditionally always been
    # returned as an integer to avoid checks at the point is used.

    if sys.platform.startswith('linux'):
        return _linux_physical_memory_used()

    # For all other platforms try using getrusage() if we have the
    # resource module available. The units returned can differ based on
    # platform. Assume 1024 byte blocks as default. Some platforms such
    # as Solaris will report zero for 'ru_maxrss', so we skip those.

    try:
        rusage = resource.getrusage(resource.RUSAGE_SELF)
    except NameError:
        pass
    else:
        if sys.platform == 'darwin':
            # On MacOS X, despite the manual page saying the
            # value is in kilobytes, it is actually in bytes.

            memory_bytes = float(rusage.ru_maxrss)
            return memory_bytes / (1024 * 1024)

        elif rusage.ru_maxrss > 0:
            memory_kbytes = float(rusage.ru_maxrss)
            return memory_kbytes / 1024

    return 0


def docker_container_id(cgroup_path='/proc/self/cgroup'):
    """Returns the docker container id, or None if it can't be determined."""

    if not sys.platform.startswith('linux'):
        return None

    container_id = None
    try:
        with open(cgroup_path, 'r') as cgroup_info:
            container_id = _process_cgroup_info(cgroup_info)
        return container_id

    except Exception:
        return None


def _process_cgroup_info(cgroup_info):
    """Parses the Docker container id from cgroup info.

    Arguments:
      cgroup_info: An iterable where each item is a line of a cgroup file.

    Returns:
      Dock container id or None if it can't be determined.

    """

    cgroup_ids = _parse_cgroup_ids(cgroup_info)
    cpu_cgroup = cgroup_ids.get('cpu', '')

    native_no_sysd_p = '^/docker/(?P<native_no_sysd>[0-9a-f]+)$'
    native_sysd_p = '^/system.slice/docker-(?P<native_sysd>[0-9a-f]+).scope$'
    lxc_p = '^/lxc/(?P<lxc>[0-9a-f]+)$'
    docker_id_p = '|'.join([native_no_sysd_p, native_sysd_p, lxc_p])

    match = re.match(docker_id_p, cpu_cgroup)
    if match:
        container_id = next((m for m in match.groups() if m is not None))
    elif cpu_cgroup == '/':
        container_id = None
    else:
        _logger.debug("Ignoring unrecognized cgroup ID format: '%s'" %
                (cpu_cgroup))
        container_id = None

    if (container_id and not _validate_docker_container_id(container_id)):
        container_id = None
        _logger.warning("Docker cgroup ID does not validate: '%s'" %
                container_id)
        # As per spec
        internal_metric('Supportability/utilization/docker/error', 1)

    return container_id


def _parse_cgroup_ids(cgroup_info):
    """Returns a dictionary of subsystems to their cgroup.

    Arguments:
      cgroup_info: An iterable where each item is a line of a cgroup file.

    """

    cgroup_ids = {}

    for line in cgroup_info:
        parts = line.split(':')
        if len(parts) != 3:
            continue

        _, subsystems, cgroup_id = parts
        subsystems = subsystems.split(',')

        for subsystem in subsystems:
            cgroup_ids[subsystem] = cgroup_id

    return cgroup_ids


def _validate_docker_container_id(container_id):
    """Validates a docker container id.

    Arguments:
      container_id: A string or buffer with the container id.

    Returns:
      True if the container id is valid, False otherwise.

    """

    # Check if container id is valid
    valid_id_p = '^[0-9a-f]+$'

    match = re.match(valid_id_p, container_id)
    if match and len(container_id) == 64:
        return True

    # Container id is not valid
    return False


_nr_cached_hostname = None
_nr_cached_hostname_lock = threading.Lock()


def gethostname():
    """Cache the output of socket.gethostname().

    Keeps the reported hostname consistent throughout an agent run.

    """

    global _nr_cached_hostname
    global _nr_cached_hostname_lock

    if _nr_cached_hostname:
        return _nr_cached_hostname

    # Only lock for the one-time write.

    with _nr_cached_hostname_lock:
        if _nr_cached_hostname is None:
            _nr_cached_hostname = socket.gethostname()

    return _nr_cached_hostname
