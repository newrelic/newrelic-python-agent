import six
import time

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)

try:
    from newrelic.core.mtb_pb2 import AttributeValue, Span
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
            record_transaction_called.append(True)
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise
            else:
                if instance.settings.mtb.endpoint:
                    # FIXME: This needs to access the deque iterator in stats
                    # engine where spans will be streamed from
                    node = args[0]
                    events = [span for span
                                   in node.span_protos(instance.settings)]
                else:
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
