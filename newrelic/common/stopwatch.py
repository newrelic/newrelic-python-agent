# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module implements a timer for measuring elapsed time. It will
attempt to use a monotonic clock where when available, or otherwise use
whatever clock has the highest resolution.

"""

import time

default_timer = time.perf_counter
timer_implementation = "time.perf_counter()"


# A timer class which deals with remembering the start time based on
# wall clock time and duration based on a monotonic clock where
# available.


class _Timer:
    def __init__(self):
        self._time_started = time.time()
        self._started = default_timer()
        self._stopped = None

    def time_started(self):
        return self._time_started

    def stop_timer(self):
        if self._stopped is None:
            self._stopped = default_timer()
        return self._stopped - self._started

    def restart_timer(self):
        elapsed_time = self.stop_timer()
        self._time_started = time.time()
        self._started = default_timer()
        self._stopped = None
        return elapsed_time

    def elapsed_time(self):
        if self._stopped is not None:
            return self._stopped - self._started
        return default_timer() - self._started


def start_timer():
    return _Timer()
