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

import six
import time

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)

try:
    from newrelic.core.infinite_tracing_pb2 import AttributeValue, Span
except:
    AttributeValue = None
    Span = None


def validate_span_events(count=1,
        exact_intrinsics={}, expected_intrinsics=[], unexpected_intrinsics=[],
        exact_agents={}, expected_agents=[], unexpected_agents=[],
        exact_users={}, expected_users=[], unexpected_users=[]):

    # Used for validating a single span event.
    #
    # Since each transaction could produce multiple span events, assert that at
    # least `count` number of those span events meet the criteria, if not,
    # raises an AssertionError.
    #
    # Use this validator once per distinct span event expected.

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):

        record_transaction_called = []
        recorded_span_events = []

        @transient_function_wrapper('newrelic.core.stats_engine',
                'StatsEngine.record_transaction')
        def capture_span_events(wrapped, instance, args, kwargs):
            events = []

            @transient_function_wrapper(
                    'newrelic.common.streaming_utils',
                    'StreamBuffer.put')
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
                    events = [event for priority, seen_at, event
                                    in instance.span_events.pq]

                recorded_span_events.append(events)

            return result

        _new_wrapper = capture_span_events(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_transaction_called
        captured_events = recorded_span_events.pop()

        mismatches = []
        matching_span_events = 0
        for captured_event in captured_events:
            if Span and isinstance(captured_event, Span):
                intrinsics = captured_event.intrinsics
                user_attrs = captured_event.user_attributes
                agent_attrs = captured_event.agent_attributes
            else:
                intrinsics, user_attrs, agent_attrs = captured_event

            _check_span_intrinsics(intrinsics)

            intrinsics_ok = _check_span_attributes(intrinsics,
                    exact_intrinsics, expected_intrinsics,
                    unexpected_intrinsics, mismatches)
            agent_attr_ok = _check_span_attributes(agent_attrs,
                    exact_agents, expected_agents,
                    unexpected_agents, mismatches)
            user_attr_ok = _check_span_attributes(user_attrs,
                    exact_users, expected_users,
                    unexpected_users, mismatches)

            if intrinsics_ok and agent_attr_ok and user_attr_ok:
                matching_span_events += 1

        def _span_details():
            details = [
                'matching_span_events=%d' % matching_span_events,
                'count=%d' % count,
                'mismatches=%s' % mismatches,
                'captured_events=%s' % captured_events
            ]

            return "\n".join(details)

        assert matching_span_events == count, _span_details()

        return val

    return _validate_wrapper


def check_value_equals(dictionary, key, expected_value):
    value = dictionary.get(key)
    if AttributeValue and isinstance(value, AttributeValue):
        for descriptor, val in value.ListFields():
            if val != expected_value:
                return False
        return True
    else:
        return value == expected_value


def assert_isinstance(value, expected_type):
    if AttributeValue and isinstance(value, AttributeValue):
        if expected_type is six.string_types:
            assert value.HasField('string_value')
        elif expected_type is float:
            assert value.HasField('double_value')
        elif expected_type is int:
            assert value.HasField('int_value')
        else:
            assert False
    else:
        assert isinstance(value, expected_type)


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
                    mismatches.append('key: %s, value:<%s><%s>' % (
                        key, value, attrs.get(key)))
                    break
            else:
                return True

    return False


def _check_span_intrinsics(intrinsics):
    assert check_value_equals(intrinsics, 'type', 'Span')
    assert_isinstance(intrinsics['traceId'], six.string_types)
    assert_isinstance(intrinsics['guid'], six.string_types)
    if 'parentId' in intrinsics:
        assert_isinstance(intrinsics['parentId'], six.string_types)
    assert_isinstance(intrinsics['transactionId'], six.string_types)
    intrinsics['sampled'] is True
    assert_isinstance(intrinsics['priority'], float)
    assert_isinstance(intrinsics['timestamp'], int)
    ts = intrinsics['timestamp']
    if AttributeValue and isinstance(ts, AttributeValue):
        ts = ts.double_value
    assert ts <= int(time.time() * 1000)
    assert_isinstance(intrinsics['duration'], float)
    assert_isinstance(intrinsics['name'], six.string_types)
    assert_isinstance(intrinsics['category'], six.string_types)
    if 'nr.entryPoint' in intrinsics:
        assert check_value_equals(intrinsics, 'nr.entryPoint', True)
