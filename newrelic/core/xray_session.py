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

from collections import namedtuple

_XraySession = namedtuple('XraySession',
        ['xray_id', 'key_txn', 'stop_time_s', 'max_traces',
            'sample_period_s'])

class XraySession(_XraySession):

    def get_trace_count(self):
        if getattr(self, '_trace_count', None) is None:
            self._trace_count = 0
        return self._trace_count

    def set_trace_count(self, count):
        self._trace_count = count

    trace_count = property(get_trace_count, set_trace_count)
