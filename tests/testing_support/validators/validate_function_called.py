from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_function_called(module, name):
    """Verify that a function is called."""

    called = []

    @transient_function_wrapper(module, name)
    def _validate_function_called(wrapped, instance, args, kwargs):
        called.append(True)
        return wrapped(*args, **kwargs)

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        new_wrapper = _validate_function_called(wrapped)
        result = new_wrapper(*args, **kwargs)
        assert called
        return result

    return wrapper
