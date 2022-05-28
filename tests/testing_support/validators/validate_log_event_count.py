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

import copy

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)
from testing_support.fixtures import catch_background_exceptions

def validate_log_event_count(count=1):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_called = []
        recorded_logs = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        @catch_background_exceptions
        def _validate_log_event_count(wrapped, instance, args, kwargs):
            record_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                recorded_logs.extend(list(instance._log_events))

            return result

        _new_wrapper = _validate_log_event_count(wrapped)
        val = _new_wrapper(*args, **kwargs)
        if count:
            assert record_called
        logs = copy.copy(recorded_logs)
        
        record_called[:] = []
        recorded_logs[:] = []

        assert count == len(logs), len(logs)

        return val

    return _validate_wrapper
