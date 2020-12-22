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


def validate_database_duration():
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_database_duration(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            metrics = instance.stats_table
            transaction_events = instance.transaction_events

            assert transaction_events.num_seen == 1

            event = next(iter(transaction_events))
            intrinsics = event[0]

            # As long as we are sending 'Database' metrics, then
            # 'databaseDuration' and 'databaseCallCount' will be
            # the sum both 'Database' and 'Datastore' values.

            try:
                database_all = metrics[('Database/all', '')]
            except KeyError:
                database_all_duration = 0.0
                database_all_call_count = 0
            else:
                database_all_duration = database_all.total_call_time
                database_all_call_count = database_all.call_count

            try:
                datastore_all = metrics[('Datastore/all', '')]
            except KeyError:
                datastore_all_duration = 0.0
                datastore_all_call_count = 0
            else:
                datastore_all_duration = datastore_all.total_call_time
                datastore_all_call_count = datastore_all.call_count

            assert 'databaseDuration' in intrinsics
            assert 'databaseCallCount' in intrinsics

            assert intrinsics['databaseDuration'] == (database_all_duration +
                    datastore_all_duration)
            assert intrinsics['databaseCallCount'] == (
                    database_all_call_count + datastore_all_call_count)

        return result

    return _validate_database_duration
