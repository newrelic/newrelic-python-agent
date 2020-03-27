from testing_support.fixtures import (override_application_settings,
        core_application_stats_engine)
from testing_support.validators.validate_span_events import (
        validate_span_events)
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction


@override_application_settings(
    {
        "distributed_tracing.enabled": True,
        "span_events.enabled": True,
    }
)
@validate_span_events(count=1)
@background_task(name="test_mtb_span_events")
def test_mtb_span_events():
    transaction = current_transaction()
    transaction._sampled = True


def test_span_stream_is_singleton():
    stats_engine = core_application_stats_engine()
    workarea = stats_engine.create_workarea()

    # The workarea span stream should be equal to the global span stream
    assert stats_engine.span_stream is workarea.span_stream
