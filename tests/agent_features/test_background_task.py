from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace


def test_nested_context_managers():
    app = application_instance()
    outer = BackgroundTask(app, 'outer')
    inner = BackgroundTask(app, 'inner')
    with outer:
        with inner:
            assert not inner.enabled


def test_sentinel_exited_complete_root_exception():
    """
    This test forces a transaction to exit while it still has an active trace
    this causes an exception to be raised in TraceCache complete_root(). It
    verifies that the sentinel.exited property is set to true if an exception
    is raised in complete_root()
    """
    expected_error = "not the current trace"

    try:
        txn = None
        sentinel = None
        txn = BackgroundTask(application_instance(), "Parent")
        txn.__enter__()
        sentinel = txn.root_span
        trace = FunctionTrace("trace")
        trace.__enter__()
        txn.__exit__(None, None, None)
        assert False, "Did not raise exception"
    except RuntimeError as e:
        assert str(e) == expected_error
    finally:
        assert sentinel.exited
