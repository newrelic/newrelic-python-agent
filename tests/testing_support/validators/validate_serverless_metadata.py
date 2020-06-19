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
