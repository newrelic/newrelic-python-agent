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

from newrelic.common.encoding_utils import json_encode
from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.packages import six


def validate_error_trace_collector_json():
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_error_trace_collector_json(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            errors = instance.error_data()

            # recreate what happens right before data is sent to the collector
            # in data_collector.py via ApplicationSession.send_errors
            agent_run_id = 666
            payload = (agent_run_id, errors)
            collector_json = json_encode(payload)

            decoded_json = json.loads(collector_json)

            assert decoded_json[0] == agent_run_id
            err = decoded_json[1][0]
            assert len(err) == 5
            assert isinstance(err[0], (int, float))
            assert isinstance(err[1], six.string_types)  # path
            assert isinstance(err[2], six.string_types)  # error message
            assert isinstance(err[3], six.string_types)  # exception name
            parameters = err[4]

            parameter_fields = ["userAttributes", "stack_trace", "agentAttributes", "intrinsics"]

            for field in parameter_fields:
                assert field in parameters

            assert "request_uri" not in parameters

        return result

    return _validate_error_trace_collector_json
