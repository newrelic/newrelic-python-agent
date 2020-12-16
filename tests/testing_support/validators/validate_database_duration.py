
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
