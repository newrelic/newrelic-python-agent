from newrelic.common.object_wrapper import (
        transient_function_wrapper,
        function_wrapper)


def validate_serverless_data(
        should_exist=True, expected_methods=(), forgone_methods=()):

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        payloads = []

        @transient_function_wrapper('newrelic.core.data_collector',
                'ServerlessModeSession.finalize')
        def _capture(wrapped, instance, args, kwargs):
            payload = instance._data.copy()
            payloads.append(payload)
            result = wrapped(*args, **kwargs)
            return result

        def _validate():
            if not should_exist:
                assert not payloads
                return

            assert payloads

            for payload in payloads:
                assert 'metric_data' in payload

                for method in expected_methods:
                    assert method in payload

                for method in forgone_methods:
                    assert method not in payload

        capture_wrapped = _capture(wrapped)
        result = capture_wrapped(*args, **kwargs)
        _validate()
        return result

    return _validate_wrapper
