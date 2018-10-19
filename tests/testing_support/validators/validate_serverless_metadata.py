from newrelic.common.encoding_utils import (serverless_payload_decode,
        json_decode)
from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_serverless_metadata(exact_metadata=None):

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
                obj = json_decode(payload)
                decoded = serverless_payload_decode(obj[2])

                assert 'metadata' in decoded
                metadata = decoded['metadata']

                if exact_metadata:
                    for key, value in exact_metadata.items():
                        assert key in metadata
                        assert metadata[key] == value, metadata

        capture_wrapped = _capture(wrapped)
        result = capture_wrapped(*args, **kwargs)
        _validate()
        return result

    return _validate_wrapper
