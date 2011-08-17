import os
import time
import sys

import newrelic.core.metric

def _cpu_count():
    """Return the number of processors host hardware provides.

    """

    # TODO For more methods of determining this if required see
    # http://stackoverflow.com/questions/1006289.

    # Python 2.6+.

    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError,NotImplementedError):
        pass

    # POSIX Systems.

    try:
        res = int(os.sysconf('SC_NPROCESSORS_ONLN'))
        if res > 0:
            return res
    except (AttributeError,ValueError):
        pass

    # Fallback to indicating only a single processor.

    return 1

class CPUSampler(object):

    # TODO Original comment in code provided by Saxon is "CPU
    # times are not sampled". Not sure what that is meant to me
    # so need to find out.

    def __init__(self):
        self._last_timestamp = time.time()
        self._times = os.times()

    def value_metrics(self):
        now = time.time()
        new_times = os.times()

        elapsed_time = now - self._last_timestamp

        user_time = new_times[0] - self._times[0]

        utilization = user_time / (elapsed_time*_cpu_count())

        self._last_timestamp = now
        self._times = new_times

        yield newrelic.core.metric.ValueMetric(
                name='CPU/User Time', value=user_time)
        yield newrelic.core.metric.ValueMetric(
                name='CPU/User/Utilization', value=utilization)

def _memory_used():
    """Returns the amount of resident memory in use in MBs.

    """

    # FIXME Not all systems use getrusage() or what they set
    # struct member to differs. Need to fill out appropriate
    # methods here for different platforms.

    try:
        import resource
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == 'darwin':
            return float(rusage.ru_maxrss) / (1024*1024)
    except:
        pass

    # Fallback to indicating no memory usage.

    return 0

class MemorySampler(object):

    def value_metrics(self):
        yield newrelic.core.metric.ValueMetric(
                name='Memory/Physical', value=_memory_used())
