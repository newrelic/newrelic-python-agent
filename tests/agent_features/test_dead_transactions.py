import gc
import pytest
import newrelic.packages.six as six

from newrelic.api.background_task import BackgroundTask
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import transient_function_wrapper, function_wrapper


@function_wrapper
def capture_errors(wrapped, instance, args, kwargs):
    ERRORS = []

    @transient_function_wrapper(
            'newrelic.api.transaction', 'Transaction.__exit__')
    def capture_errors(wrapped, instance, args, kwargs):
        try:
            return wrapped(*args, **kwargs)
        except Exception as e:
            ERRORS.append(e)
            raise

    result = capture_errors(wrapped)(*args, **kwargs)

    assert not ERRORS
    return result


@pytest.mark.parametrize('circular', (True, False))
@capture_errors
def test_dead_transaction_ends(circular):
    if circular and six.PY2:
        pytest.skip("Circular references in py2 result in a memory leak. "
                "There is no way to remove transactions from the weakref "
                "cache in this case.")

    transaction = BackgroundTask(
            application_instance(), "test_dead_transaction_ends")
    if circular:
        transaction._self = transaction

    transaction.__enter__()
    del transaction
    gc.collect()
