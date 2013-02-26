import os
import sys

try:
    import resource
except:
    pass

from newrelic.core.data_source import data_source_generator

def memory_used():
    """Returns the amount of resident memory in use in MBs.

    """

    # FIXME  Need to fill out appropriate methods here for
    # different platforms.

    # For Linux use the proc filesystem. Use 'statm' as easier
    # to parse than 'status' file.
    #
    #   /proc/[number]/statm
    #          Provides information about memory usage, measured in pages.
    #          The columns are:
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
        except:
            pass
        finally:
            if fp:
                fp.close()

    # Fallback to trying to use getrusage(). The units returned
    # can differ based on platform. Assume 1024 byte blocks as
    # default.

    if 'resource' in sys.modules:
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == 'darwin':
            # On MacOS X, despite the manual page saying the
            # value is in kilobytes, it is actually in bytes.

            memory_bytes = float(rusage.ru_maxrss)
            return memory_bytes / (1024*1024)
        else:
            memory_kbytes = float(rusage.ru_maxrss)
            return memory_kbytes / 1024

    # Fallback to indicating no memory usage.

    return 0

@data_source_generator(name='Memory Usage')
def memory_usage_data_source():
    yield ('Memory/Physical', memory_used())
