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

import json

from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.common.encoding_utils import json_encode


def validate_transaction_exception_message(expected_message):
    """Test exception message encoding/decoding for a single error"""

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_transaction_exception_message(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            error_data = instance.error_data()
            assert len(error_data) == 1
            error = error_data[0]

            # make sure we have the one error we are testing

            # Because we ultimately care what is sent to APM, run the exception
            # data through the encoding code that is would be run through
            # before being sent to the collector.

            encoded_error = json_encode(error)

            # to decode, use un-adultered json loading methods

            decoded_json = json.loads(encoded_error)

            message = decoded_json[2]
            assert expected_message == message

        return result

    return _validate_transaction_exception_message