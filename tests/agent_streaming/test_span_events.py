from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_span_events import (
        validate_span_events)
from newrelic.api.background_task import background_task
from newrelic.api.transaction import current_transaction


@override_application_settings(
    {
        "distributed_tracing.enabled": True,
        "span_events.enabled": True,
        "mtb.endpoint": True,
    }
)
@validate_span_events(count=1)
@background_task(name="test_mtb_span_events")
def test_mtb_span_events():
    transaction = current_transaction()
    transaction._sampled = True
