from newrelic.common.encoding_utils import (serverless_payload_decode,
        json_decode)
from newrelic.common.object_wrapper import (
        transient_function_wrapper,
        function_wrapper)


def validate_serverless_payload():

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        payloads = []

        @transient_function_wrapper('newrelic.core.data_collector',
                'ServerlessModeSession.finalize')
        def _capture(wrapped, instance, args, kwargs):
            payload = wrapped(*args, **kwargs)
            payloads.append(payload)
            return payload

        def _validate():
            assert payloads

            for payload in payloads:
                assert isinstance(payload, str)

                obj = json_decode(payload)

                assert len(obj) == 3, obj

                assert obj[0] == 1  # Version = 1
                assert obj[1] == 'NR_LAMBDA_MONITORING'  # Marker

                decoded = serverless_payload_decode(obj[2])

                # Keys should only contain metadata / data
                set(decoded.keys()) == set(('metadata', 'data'))

        capture_wrapped = _capture(wrapped)
        result = capture_wrapped(*args, **kwargs)
        _validate()
        return result

    return _validate_wrapper
