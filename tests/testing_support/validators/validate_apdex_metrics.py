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

from testing_support.fixtures import catch_background_exceptions
from newrelic.common.object_wrapper import (
        transient_function_wrapper,
        function_wrapper)


def validate_apdex_metrics(name, group='Function', count=1,
        apdex_t_min=0.5, apdex_t_max=0.5):

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        record_transaction_called = []
        recorded_metrics = []

        @transient_function_wrapper('newrelic.core.stats_engine',
                'StatsEngine.record_transaction')
        @catch_background_exceptions
        def _capture_metrics(wrapped, instance, args, kwargs):
            record_transaction_called.append(True)
            result = wrapped(*args, **kwargs)
            recorded_metrics.append(instance.stats_table)
            return result

        def _validate():
            metric_name = 'Apdex/%s/%s' % (group, name)
            key = (metric_name, '')

            metric = recorded_metrics.get(key)

            # Sum of satisfying / tolerating / frustrating must equal count
            assert sum(metric[:2]) == count, metric[:2]

            # Check apdex_t range
            assert metric[3] == apdex_t_min, metric[3]
            assert metric[4] == apdex_t_max, metric[4]

            # Last field is always 0
            assert metric[5] == 0

        _new_wrapper = _capture_metrics(wrapped)
        result = _new_wrapper(*args, **kwargs)
        assert record_transaction_called
        recorded_metrics = recorded_metrics.pop()
        _validate()
        return result

    return _validate_wrapper
