from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_span_events(exact_intrinsics={}, expected_intrinsics=[],
                         unexpected_intrinsics=[], count=1):

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
                events = [event for priority, event in instance.span_events.pq]
                recorded_span_events.append(events)

            return result

        _new_wrapper = capture_span_events(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert record_transaction_called
        captured_events = recorded_span_events.pop()

        mismatches = []
        matching_span_events = 0
        for captured_event in captured_events:
            intrinsics, agent_attrs, user_attrs = captured_event

            # for now we do not add any of these attr types to span events
            assert not agent_attrs
            assert not user_attrs

            for expected_intrinsic in expected_intrinsics:
                if expected_intrinsic not in intrinsics:
                    break
            else:
                for unexpected_intrinsic in unexpected_intrinsics:
                    if unexpected_intrinsic in intrinsics:
                        break
                else:
                    for key, value in exact_intrinsics.items():
                        if intrinsics.get(key) != value:
                            mismatches.append('key: %s, value:<%s><%s>' % (
                                key, value, intrinsics.get(key)))
                            break
                    else:
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
