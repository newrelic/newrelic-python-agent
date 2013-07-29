"""This module implements a data source for generating metrics about CPU
usage.

"""

import os
import time

from ..common.system_info import cpu_count

from .decorators import data_source_factory

@data_source_factory(name='CPU Usage')
class _CPUUsageDataSource(object):

    def __init__(self, settings, environ):
        self._last_timestamp = None
        self._times = None

    def start(self):
        self._last_timestamp = time.time()
        try:
            self._times = os.times()
        except Exception:
            self._times = None

    def stop(self):
        self._last_timestamp = None
        self._times = None

    def __call__(self):
        if self._times is None:
            return

        now = time.time()
        new_times = os.times()

        elapsed_time = now - self._last_timestamp

        user_time = new_times[0] - self._times[0]

        utilization = user_time / (elapsed_time*cpu_count())

        self._last_timestamp = now
        self._times = new_times

        yield ('CPU/User Time', user_time)
        yield ('CPU/User/Utilization', utilization)

cpu_usage_data_source = _CPUUsageDataSource
