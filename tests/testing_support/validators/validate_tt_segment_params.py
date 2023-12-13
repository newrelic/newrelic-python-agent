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

from newrelic.common.encoding_utils import unpack_field
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from newrelic.core.database_utils import SQLConnections


def validate_tt_segment_params(forgone_params=(), present_params=(), exact_params=None):
    exact_params = exact_params or {}
    recorded_traces = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _extract_trace(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        # Now that transaction has been recorded, generate
        # a transaction trace

        connections = SQLConnections()
        trace_data = instance.transaction_trace_data(connections)
        # Save the recorded traces
        recorded_traces.extend(trace_data)

        return result

    @function_wrapper
    def validator(wrapped, instance, args, kwargs):
        new_wrapper = _extract_trace(wrapped)
        result = new_wrapper(*args, **kwargs)

        # Verify that traces have been recorded
        assert recorded_traces

        # Extract the first transaction trace
        transaction_trace = recorded_traces[0]
        pack_data = unpack_field(transaction_trace[4])

        # Extract the root segment from the root node
        root_segment = pack_data[0][3]

        recorded_params = {}

        def _validate_segment_params(segment):
            segment_params = segment[3]

            # Translate from the string cache
            for key, value in segment_params.items():
                if hasattr(value, "startswith") and value.startswith("`"):
                    try:
                        index = int(value[1:])
                        value = pack_data[1][index]
                    except ValueError:
                        pass
                segment_params[key] = value

            recorded_params.update(segment_params)

            for child_segment in segment[4]:
                _validate_segment_params(child_segment)

        _validate_segment_params(root_segment)

        recorded_params_set = set(recorded_params.keys())

        # Verify that the params in present params have been recorded
        present_params_set = set(present_params)
        assert recorded_params_set.issuperset(present_params_set)

        # Verify that all forgone params are omitted
        recorded_forgone_params = recorded_params_set & set(forgone_params)
        assert not recorded_forgone_params

        # Verify that all exact params are correct
        for key, value in exact_params.items():
            assert recorded_params[key] == value

        return result

    return validator
