from newrelic.common.object_wrapper import transient_function_wrapper, function_wrapper


def validate_sql_obfuscation(expected_sqls):

    actual_sqls = []

    @transient_function_wrapper("newrelic.core.database_node", "DatabaseNode.__new__")
    def _validate_sql_obfuscation(wrapped, instance, args, kwargs):
        node = wrapped(*args, **kwargs)
        actual_sqls.append(node.formatted)
        return node

    @function_wrapper
    def _validate(wrapped, instance, args, kwargs):
        new_wrapper = _validate_sql_obfuscation(wrapped)
        result = new_wrapper(*args, **kwargs)

        for expected_sql in expected_sqls:
            assert expected_sql in actual_sqls, (expected_sql, actual_sqls)

        return result

    return _validate
