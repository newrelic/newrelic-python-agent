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

import newrelic.core.attribute as attribute

from newrelic.core.metric import TimeMetric


_LogNode = namedtuple('_LogNode',
        ['timestamp', 'log_level', 'message','logger_name'])


class LogNode(_LogNode):

    # def __new__(cls, *args, **kwargs):
    #     node = _LogNode.__new__(cls, *args, **kwargs)
    #     return node

    # @property
    # def timestamp(self):
    #     return self._timestamp

    # @property
    # def log_level(self):
    #     return self._log_level

    # @property
    # def message(self):
    #     return self._message

    # @property
    # def logger_name(self):
    #     return self._logger_name


    def time_metrics(self, stats, root, parent):
        """Return a generator yielding the timed metrics for this log node"""

        total_log_lines_metric_name = 'Logging/lines'

        severity_log_lines_metric_name = 'Logging/lines/%s' % self.log_level

        yield TimeMetric(name=total_log_lines_metric_name, scope="",
                    duration=0.0, exclusive=None)

        yield TimeMetric(name=severity_log_lines_metric_name, scope="",
                         duration=0.0, exclusive=None)

