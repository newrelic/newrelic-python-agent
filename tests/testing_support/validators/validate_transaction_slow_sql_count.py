from newrelic.common.object_wrapper import (function_wrapper,
                                            transient_function_wrapper)
from newrelic.core.database_utils import SQLConnections


def validate_transaction_slow_sql_count(num_slow_sql):
    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _validate_transaction_slow_sql_count(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)
        connections = SQLConnections()

        with connections:
            slow_sql_traces = instance.slow_sql_data(connections)
            assert len(slow_sql_traces) == num_slow_sql

        return result

    return _validate_transaction_slow_sql_count
