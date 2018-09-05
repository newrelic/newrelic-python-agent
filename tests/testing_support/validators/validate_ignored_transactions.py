from newrelic.common.object_wrapper import (transient_function_wrapper,
                                            function_wrapper)


# check that the number of ignored transactions seen, either in total or
# specific to ones with a particular name, is the same as "count"
def validate_ignored_transactions(name=None, count=1):
    counted = []

    @transient_function_wrapper('newrelic.api.transaction',
                                'Transaction.__exit__')
    def _count_ignored_transactions(wrapped, instance, args, kwargs):
        if (instance.ignore_transaction) and (
                (name is None) or (instance.name == name)):
            counted.append(1)

        return wrapped(*args, **kwargs)

    @function_wrapper
    def _validate_ignored_count(wrapped, instance, args, kwargs):
        _new_wrapper = _count_ignored_transactions(wrapped)
        result = _new_wrapper(*args, **kwargs)

        assert sum(counted) == count
        return result

    return _validate_ignored_count
