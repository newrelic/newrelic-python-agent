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

import time

from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper


def validate_spanlink_or_spanevent_events(
    count=1,
    exact_intrinsics=None,
    expected_intrinsics=None,
    exact_users=None,
    expected_users=None,
    unexpected_users=None,
    index=-1,
):
    # Used for validating a single SpanLink or SpanEvent event.
    #
    # Since each transaction could produce multiple SpanLink or SpanEvent events,
    # assert that at least `count` number of those SpanLink or SpanEvent events
    # meet the criteria.  If not, raises an AssertionError.
    #
    # Use this validator once per distinct SpanLink or SpanEvent event expected.

    if unexpected_users is None:
        unexpected_users = []
    if expected_users is None:
        expected_users = []
    if exact_users is None:
        exact_users = {}
    if exact_intrinsics is None:
        exact_intrinsics = {}
    if expected_intrinsics is None:
        expected_intrinsics = []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        record_transaction_called = []
        recorded_span_events = []

        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        def capture_spanlink_spanevent_events(wrapped, instance, args, kwargs):
            events = []

            @transient_function_wrapper("newrelic.common.streaming_utils", "StreamBuffer.put")
            def stream_capture(wrapped, instance, args, kwargs):
                event = args[0]
                events.append(event)
                return wrapped(*args, **kwargs)

            record_transaction_called.append(True)
            try:
                result = stream_capture(wrapped)(*args, **kwargs)
            except:
                raise
            else:
                if not instance.settings.infinite_tracing.enabled:
                    events = [event for priority, seen_at, event in instance.span_events.pq]

                recorded_span_events.append(events)

            return result

        _new_wrapper = capture_spanlink_spanevent_events(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_transaction_called
        captured_events = recorded_span_events.pop(index)

        mismatches = []
        matching_span_events = 0
        for captured_event in captured_events:
            if isinstance(captured_event[0], list):
                for events in captured_event[1:]:
                    for event in events:
                        intrinsics, user_attrs, _ = event
                        _check_otel_event_intrinsics(intrinsics)

                        intrinsics_ok = _check_span_attributes(
                            intrinsics, exact_intrinsics, expected_intrinsics, [], mismatches
                        )
                        user_attr_ok = _check_span_attributes(
                            user_attrs, exact_users, expected_users, unexpected_users, mismatches
                        )

                        if intrinsics_ok and user_attr_ok:
                            matching_span_events += 1

        def _span_details():
            details = [
                f"matching_span_events={matching_span_events}",
                f"count={count}",
                f"mismatches={mismatches}",
                f"captured_events={captured_events}",
            ]

            return "\n".join(details)

        assert matching_span_events == count, _span_details()

        return val

    return _validate_wrapper


def check_value_equals(dictionary, key, expected_value):
    value = dictionary.get(key)
    return value == expected_value


def _check_span_attributes(attrs, exact, expected, unexpected, mismatches):
    for expected_attribute in expected:
        if expected_attribute not in attrs:
            break
    else:
        for unexpected_attribute in unexpected:
            if unexpected_attribute in attrs:
                break
        else:
            for key, value in exact.items():
                if not check_value_equals(attrs, key, value):
                    mismatches.append(f"key: {key}, value:<{value}><{attrs.get(key)}>")
                    break
            else:
                return True

    return False


def _check_otel_event_intrinsics(intrinsics):
    assert check_value_equals(intrinsics, "type", "SpanEvent") or check_value_equals(intrinsics, "type", "SpanLink")
    assert isinstance(intrinsics["trace.id"], str)
    assert isinstance(intrinsics["timestamp"], int)
    ts = intrinsics["timestamp"]
    assert ts <= int(time.time() * 1000)
    if intrinsics["type"] == "SpanLink":
        assert isinstance(intrinsics["id"], str)
        assert isinstance(intrinsics["linkedSpanId"], str)
        assert isinstance(intrinsics["linkedTraceId"], str)
    elif intrinsics["type"] == "SpanEvent":
        assert isinstance(intrinsics["span.id"], str)
        assert isinstance(intrinsics["name"], str)
    else:
        return False
