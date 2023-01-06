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


def validate_custom_events(events):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_called = []
        recorded_events = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        @catch_background_exceptions
        def _validate_custom_events(wrapped, instance, args, kwargs):
            record_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                txn = args[0]
                recorded_events[:] = []
                recorded_events.extend(list(txn.custom_events))

            return result


        _new_wrapper = _validate_custom_events(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_called
        custom_events = copy.copy(recorded_events)
        
        record_called[:] = []
        recorded_events[:] = []
        for expected in events:
            matching_custom_events = 0
            mismatches = []
            for captured in custom_events:
                if _check_custom_event_attributes(expected, captured, mismatches):
                    matching_custom_events += 1
            assert matching_custom_events == 1, _custom_event_details(matching_custom_events, custom_events, mismatches)

        return val


    def _check_custom_event_attributes(expected, captured, mismatches):
        assert len(captured) == 2  # [intrinsic, user attributes]
        expected_intrinsics = expected.get("intrinsics", {})
        expected_users = expected.get("users", {})
        intrinsics = captured[0]
        users = captured[1]

        def _validate(expected, captured):
            for key, value in six.iteritems(expected):
                if key in captured:
                    captured_value = captured[key]
                else:
                    mismatches.append("key: %s, value:<%s><%s>" % (key, value, getattr(captured, key, None)))
                    return False

                if value is not None:
                    if value != captured_value:
                        mismatches.append("key: %s, value:<%s><%s>" % (key, value, captured_value))
                        return False

            return True

        return _validate(expected_intrinsics, intrinsics) and _validate(expected_users, users)


    def _custom_event_details(matching_custom_events, captured, mismatches):
        details = [
            "matching_custom_events=%d" % matching_custom_events,
            "mismatches=%s" % mismatches,
            "captured_events=%s" % captured,
        ]

        return "\n".join(details)

    return _validate_wrapper
