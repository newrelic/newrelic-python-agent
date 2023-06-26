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
import time

from testing_support.fixtures import catch_background_exceptions

from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from newrelic.packages import six


def validate_ml_events(events):
    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_called = []
        recorded_events = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        @catch_background_exceptions
        def _validate_ml_events(wrapped, instance, args, kwargs):
            record_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            recorded_events[:] = []
            recorded_events.extend(list(instance._ml_events))

            return result

        _new_wrapper = _validate_ml_events(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_called
        found_events = copy.copy(recorded_events)

        record_called[:] = []
        recorded_events[:] = []

        for expected in events:
            matching_ml_events = 0
            mismatches = []
            for captured in found_events:
                if _check_event_attributes(expected, captured, mismatches):
                    matching_ml_events += 1
            assert matching_ml_events == 1, _event_details(matching_ml_events, events, mismatches)

        return val

    return _validate_wrapper


def _check_event_attributes(expected, captured, mismatches):
    assert len(captured) == 2  # [intrinsic, user attributes]

    intrinsics = captured[0]

    if intrinsics["type"] != expected[0]["type"]:
        mismatches.append("key: type, value:<%s><%s>" % (expected[0]["type"], captured[0].get("type", None)))
        return False

    now = time.time()

    if not (isinstance(intrinsics["timestamp"], int) and intrinsics["timestamp"] <= 1000.0 * now):
        mismatches.append("key: timestamp, value:<%s>" % intrinsics["timestamp"])
        return False

    captured_keys = set(six.iterkeys(captured[1]))
    expected_keys = set(six.iterkeys(expected[1]))
    extra_keys = captured_keys - expected_keys

    if extra_keys:
        mismatches.append("extra_keys: %s" % str(tuple(extra_keys)))
        return False

    for key, value in six.iteritems(expected[1]):
        if key in captured[1]:
            captured_value = captured[1].get(key, None)
        else:
            mismatches.append("key: %s, value:<%s><%s>" % (key, value, captured[1].get(key, None)))
            return False

        if value is not None:
            if value != captured_value:
                mismatches.append("key: %s, value:<%s><%s>" % (key, value, captured_value))
                return False

    return True


def _event_details(matching_ml_events, captured, mismatches):
    details = [
        "matching_ml_events=%d" % matching_ml_events,
        "mismatches=%s" % mismatches,
        "captured_events=%s" % captured,
    ]

    return "\n".join(details)
