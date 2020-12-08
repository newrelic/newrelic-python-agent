from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_transaction_count(count):
    _count = []

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _increment_count(wrapped, instance, args, kwargs):
        _count.append(True)
        return wrapped(*args, **kwargs)

    @function_wrapper
    def _validate_transaction_count(wrapped, instance, args, kwargs):
        _new_wrapped = _increment_count(wrapped)
        result = _new_wrapped(*args, **kwargs)
        assert len(_count) == count

        return result

    return _validate_transaction_count
