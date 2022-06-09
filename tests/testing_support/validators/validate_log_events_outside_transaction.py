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

from newrelic.packages import six

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)
from testing_support.fixtures import catch_background_exceptions

def validate_log_events_outside_transaction(events):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_called = []
        recorded_logs = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_log_event")
        @catch_background_exceptions
        def _validate_log_events_outside_transaction(wrapped, instance, args, kwargs):
            record_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                recorded_logs[:] = []
                recorded_logs.extend(list(instance._log_events))

            return result


        _new_wrapper = _validate_log_events_outside_transaction(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_called
        logs = copy.copy(recorded_logs)
        
        record_called[:] = []
        recorded_logs[:] = []

        for expected in events:
            matching_log_events = 0
            mismatches = []
            for captured in logs:
                if _check_log_attributes(expected, captured, mismatches):
                    matching_log_events += 1
            assert matching_log_events == 1, _log_details(matching_log_events, logs, mismatches)

        return val


    def _check_log_attributes(expected, captured, mismatches):
        for key, value in six.iteritems(expected):
            if hasattr(captured, key):
                captured_value = getattr(captured, key, None)
            elif key in captured.attributes:
                captured_value = captured.attributes[key]
            else:
                mismatches.append("key: %s, value:<%s><%s>" % (key, value, getattr(captured, key, None)))
                return False

            if value is not None:
                if value != captured_value:
                    mismatches.append("key: %s, value:<%s><%s>" % (key, value, captured_value))
                    return False

        return True

    def _log_details(matching_log_events, captured, mismatches):
        details = [
            "matching_log_events=%d" % matching_log_events,
            "mismatches=%s" % mismatches,
            "captured_events=%s" % captured,
        ]

        return "\n".join(details)

    return _validate_wrapper
