
from newrelic.common.object_wrapper import transient_function_wrapper

from testing_support.fixtures import catch_background_exceptions


def validate_database_trace_inputs(sql_parameters_type):

    @transient_function_wrapper('newrelic.api.database_trace',
            'DatabaseTrace.__init__')
    @catch_background_exceptions
    def _validate_database_trace_inputs(wrapped, instance, args, kwargs):
        def _bind_params(sql, dbapi2_module=None,
                connect_params=None, cursor_params=None, sql_parameters=None,
                execute_params=None, host=None, port_path_or_id=None,
                database_name=None):
            return (sql, dbapi2_module, connect_params,
                    cursor_params, sql_parameters, execute_params)

        (sql, dbapi2_module, connect_params, cursor_params,
            sql_parameters, execute_params) = _bind_params(*args, **kwargs)

        assert hasattr(dbapi2_module, 'connect')

        assert connect_params is None or isinstance(connect_params, tuple)

        if connect_params is not None:
            assert len(connect_params) == 2
            assert isinstance(connect_params[0], tuple)
            assert isinstance(connect_params[1], dict)

        assert cursor_params is None or isinstance(cursor_params, tuple)

        if cursor_params is not None:
            assert len(cursor_params) == 2
            assert isinstance(cursor_params[0], tuple)
            assert isinstance(cursor_params[1], dict)

        assert sql_parameters is None or isinstance(
                sql_parameters, sql_parameters_type)

        if execute_params is not None:
            assert len(execute_params) == 2
            assert isinstance(execute_params[0], tuple)
            assert isinstance(execute_params[1], dict)

        return wrapped(*args, **kwargs)

    return _validate_database_trace_inputs

