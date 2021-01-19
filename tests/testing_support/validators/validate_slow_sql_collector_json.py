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
from newrelic.common.constants import LOCALHOST_EQUIVALENTS
from newrelic.core.database_utils import SQLConnections
from newrelic.packages import six


def validate_slow_sql_collector_json(required_params=set(),
        forgone_params=set(), exact_params=None):
    """Check that slow_sql json output is in accordance with agent specs.
    """
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_slow_sql_collector_json(wrapped, instance, args, kwargs):
        legal_param_keys = set([
            'explain_plan',
            'backtrace',
            'host',
            'port_path_or_id',
            'database_name',
            'parent.type',
            'parent.app',
            'parent.account',
            'parent.transportType',
            'parent.transportDuration',
            'guid',
            'traceId',
            'priority',
            'sampled',
        ])
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            connections = SQLConnections()
            slow_sql_list = instance.slow_sql_data(connections)

            for slow_sql in slow_sql_list:
                assert isinstance(slow_sql[0], six.string_types)  # txn_name
                assert isinstance(slow_sql[1], six.string_types)  # txn_url
                assert isinstance(slow_sql[2], int)               # sql_id
                assert isinstance(slow_sql[3], six.string_types)  # sql
                assert isinstance(slow_sql[4], six.string_types)  # metric_name
                assert isinstance(slow_sql[5], int)               # count
                assert isinstance(slow_sql[6], float)             # total
                assert isinstance(slow_sql[7], float)             # min
                assert isinstance(slow_sql[8], float)             # max
                assert isinstance(slow_sql[9], six.string_types)  # params

                params = slow_sql[9]
                data = unpack_field(params)

                # only legal keys should be reported
                assert len(set(data.keys()) - legal_param_keys) == 0

                # if host is reported, it cannot be localhost
                if 'host' in data:
                    assert data['host'] not in LOCALHOST_EQUIVALENTS

                if required_params:
                    for param in required_params:
                        assert param in data

                if forgone_params:
                    for param in forgone_params:
                        assert param not in data

                if exact_params:
                    for param, value in exact_params.items():
                        assert param in data
                        assert data[param] == value

        return result

    return _validate_slow_sql_collector_json
