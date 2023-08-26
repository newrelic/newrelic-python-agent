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

from testing_support.fixtures import catch_background_exceptions
from testing_support.validators.validate_ml_events import (
    _check_event_attributes,
    _event_details,
)

from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper


def validate_ml_events_outside_transaction(events):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_called = []
        recorded_events = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_ml_event")
        @catch_background_exceptions
        def _validate_ml_events_outside_transaction(wrapped, instance, args, kwargs):
            record_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            recorded_events[:] = []
            recorded_events.extend(list(instance._ml_events))

            return result

        _new_wrapper = _validate_ml_events_outside_transaction(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_called
        events = copy.copy(recorded_events)

        record_called[:] = []
        recorded_events[:] = []

        for expected in events:
            matching_ml_events = 0
            mismatches = []
            for captured in events:
                if _check_event_attributes(expected, captured, mismatches):
                    matching_ml_events += 1
            assert matching_ml_events == 1, _event_details(matching_ml_events, events, mismatches)

        return val

    return _validate_wrapper
