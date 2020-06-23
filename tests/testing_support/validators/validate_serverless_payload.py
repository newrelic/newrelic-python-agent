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
from newrelic.common.object_wrapper import (
        transient_function_wrapper,
        function_wrapper)


def validate_serverless_payload(count=1):

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
            assert len(payloads) == count

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
