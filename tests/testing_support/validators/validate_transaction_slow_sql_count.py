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

from newrelic.common.object_wrapper import transient_function_wrapper
from newrelic.core.database_utils import SQLConnections


def validate_transaction_slow_sql_count(num_slow_sql):
    @transient_function_wrapper(
        "newrelic.core.stats_engine", "StatsEngine.record_transaction"
    )
    def _validate_transaction_slow_sql_count(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        connections = SQLConnections()

        with connections:
            slow_sql_traces = instance.slow_sql_data(connections)
            assert len(slow_sql_traces) == num_slow_sql

        return result

    return _validate_transaction_slow_sql_count
