import logging

from newrelic.api.transaction import end_of_transaction
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace


from testing_support.fixtures import validate_transaction_metrics


@validate_transaction_metrics(
    'test_trace_after_end_of_transaction',
    background_task=True,
    scoped_metrics=[('Function/foobar', None)],
)
@background_task(name='test_trace_after_end_of_transaction')
def test_trace_after_end_of_transaction(caplog):
    end_of_transaction()
    with FunctionTrace("foobar"):
        pass

    error_messages = [record for record in caplog.records
            if record.levelno >= logging.ERROR]
    assert not error_messages
