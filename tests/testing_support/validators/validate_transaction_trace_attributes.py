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

from testing_support.fixtures import check_attributes

from newrelic.common.encoding_utils import unpack_field
from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from newrelic.core.database_utils import SQLConnections


def validate_transaction_trace_attributes(
    required_params=None, forgone_params=None, should_exist=True, url=None, index=-1
):
    required_params = required_params or {}
    forgone_params = forgone_params or {}

    trace_data = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_transaction_trace_attributes(wrapped, instance, args, kwargs):

        result = wrapped(*args, **kwargs)

        # Now that transaction has been recorded, generate
        # a transaction trace

        connections = SQLConnections()
        _trace_data = instance.transaction_trace_data(connections)
        trace_data.append(_trace_data)

        return result

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        _new_wrapper = _validate_transaction_trace_attributes(wrapped)
        result = _new_wrapper(*args, **kwargs)

        _trace_data = trace_data[index]
        trace_data[:] = []

        if url is not None:
            trace_url = _trace_data[0][3]
            assert url == trace_url

        pack_data = unpack_field(_trace_data[0][4])
        assert len(pack_data) == 2
        assert len(pack_data[0]) == 5
        parameters = pack_data[0][4]

        assert "intrinsics" in parameters
        assert "userAttributes" in parameters
        assert "agentAttributes" in parameters

        check_attributes(parameters, required_params, forgone_params)

        return result

    return wrapper
