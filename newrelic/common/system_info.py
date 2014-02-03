"""This module implements functions for querying properties of the operating
system or for the specific process the code is running in.

"""

import os
import sys
import multiprocessing
import re

try:
    import resource
except ImportError:
    pass

def cpu_count():
    """Returns the number of CPUs in the system.

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
            if expr.match(pd) != None:
                res += 1

        if res > 0:
            return res
    except OSError:
        pass

    # Fallback to assuming only a single CPU.

    return 1

def memory_total():
    """Returns the total physical memory available in the system.

    """

    # For Linux we can determine it from the proc filesystem.

    if sys.platform == 'linux2':
        try:
            parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')

            fp = None

            try:
                fp = open('/proc/meminfo')

                for line in fp.readlines():
                    match = parser.match(line)
                    if not match:
                        continue
                    key, value = match.groups(['key', 'value'])
                    if key == 'MemTotal':
                        memory_bytes = float(value) * 1024
                        return memory_bytes / (1024*1024)

            except Exception:
                pass

            finally:
                if fp:
                    fp.close()

        except IOError:
            pass

    # For other platforms, how total system memory is calculated varies
    # and can't always be done using just what is available in the
    # Python standard library. Take a punt here and see if 'psutil' is
    # available and use the value it generates for total memory. We
    # simply ignore any exception that may occur because even though
    # psutil may be available it can fail badly if used on a
    # containerised Linux hosting service where they don't for example
    # make the /proc filesystem available.

    # NOTE Although now ignore any exceptions which can result if psutil
    # fails, in most cases never get here and if we do likely will still
    # fail. Only case where might get used is Solaris and have so few
    # deploys for that is likely not worth it at this point.

    #try:
    #    import psutil
    #    return psutil.virtual_memory().total
    #except Exception:
    #    pass

    return 0

def memory_used():
    """Returns the memory used in MBs. Calculated differently depending
    on the platform and designed for informational purposes only.

    """

    # For Linux use the proc filesystem. Use 'statm' as easier
    # to parse than 'status' file.
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

    if sys.platform == 'linux2':
        pid = os.getpid()
        statm = '/proc/%d/statm' % pid
        fp = None

        try:
            fp = open(statm, 'r')
            rss_pages = float(fp.read().split()[1])
            memory_bytes = rss_pages * resource.getpagesize()
            return memory_bytes / (1024*1024)
        except Exception:
            pass
        finally:
            if fp:
                fp.close()

    # Try using getrusage() if we have the resource module
    # available. The units returned can differ based on
    # platform. Assume 1024 byte blocks as default. Some
    # platforms such as Solaris will report zero for
    # 'ru_maxrss', so we skip those.


    try:
        rusage = resource.getrusage(resource.RUSAGE_SELF)
    except NameError:
        pass
    else:
        if sys.platform == 'darwin':
            # On MacOS X, despite the manual page saying the
            # value is in kilobytes, it is actually in bytes.

            memory_bytes = float(rusage.ru_maxrss)
            return memory_bytes / (1024*1024)

        elif rusage.ru_maxrss > 0:
            memory_kbytes = float(rusage.ru_maxrss)
            return memory_kbytes / 1024

    # For other platforms, how used memory is calculated varies
    # and can't always be done using just what is available in
    # the Python standard library. Take a punt here and see if
    # 'psutil' is available and use the value it generates for
    # total memory.

    # NOTE This is currently not used as this isn't generally
    # going to return resident memory usage (RSS) and what it
    # does return can be very much greater than what one would
    # expect. As a result it can be misleading/confusing and so
    # figure it is best not to use it.

    #try:
    #    import psutil
    #    memory_bytes = psutil.virtual_memory().used
    #    return memory_bytes / (1024*1024)
    #except ImportError, AttributeError:
    #    pass

    # Fallback to indicating no memory usage.

    return 0
