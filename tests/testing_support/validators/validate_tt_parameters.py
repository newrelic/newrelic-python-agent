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


def validate_tt_parameters(required_params=None, forgone_params=None):
    required_params = required_params or {}
    forgone_params = forgone_params or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_tt_parameters(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise

        # Now that transaction has been recorded, generate
        # a transaction trace

        connections = SQLConnections()
        trace_data = instance.transaction_trace_data(connections)
        pack_data = unpack_field(trace_data[0][4])
        tt_intrinsics = pack_data[0][4]["intrinsics"]

        for name in required_params:
            assert name in tt_intrinsics, "name=%r, intrinsics=%r" % (name, tt_intrinsics)
            assert tt_intrinsics[name] == required_params[name], "name=%r, value=%r, intrinsics=%r" % (
                name,
                required_params[name],
                tt_intrinsics,
            )

        for name in forgone_params:
            assert name not in tt_intrinsics, "name=%r, intrinsics=%r" % (name, tt_intrinsics)

        return result

    return _validate_tt_parameters
