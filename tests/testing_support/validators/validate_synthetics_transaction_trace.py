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
from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.core.database_utils import SQLConnections


def validate_synthetics_transaction_trace(required_params=None, forgone_params=None, should_exist=True):
    required_params = required_params or {}
    forgone_params = forgone_params or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_synthetics_transaction_trace(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            # Now that transaction has been recorded, generate
            # a transaction trace

            connections = SQLConnections()
            trace_data = instance.transaction_trace_data(connections)

            # Check that synthetics resource id is in TT header

            header = trace_data[0]
            header_key = "synthetics_resource_id"

            if should_exist:
                assert header_key in required_params
                assert header[9] == required_params[header_key], f"name={header_key!r}, header={header!r}"
            else:
                assert header[9] is None

            # Check that synthetics ids are in TT custom params

            pack_data = unpack_field(trace_data[0][4])
            tt_intrinsics = pack_data[0][4]["intrinsics"]

            for name in required_params:
                assert name in tt_intrinsics, f"name={name!r}, intrinsics={tt_intrinsics!r}"
                assert tt_intrinsics[name] == required_params[name], f"name={name!r}, value={required_params[name]!r}, intrinsics={tt_intrinsics!r}"

            for name in forgone_params:
                assert name not in tt_intrinsics, f"name={name!r}, intrinsics={tt_intrinsics!r}"

        return result

    return _validate_synthetics_transaction_trace
