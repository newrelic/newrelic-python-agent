import newrelic.tests.test_cases
from newrelic.core.attribute_filter import (DST_ALL, DST_SPAN_EVENTS,
        DST_BROWSER_MONITORING, DST_TRANSACTION_SEGMENTS, DST_ERROR_COLLECTOR,
        DST_TRANSACTION_TRACER, DST_TRANSACTION_EVENTS, DST_NONE)
from newrelic.core.config import finalize_application_settings


class TestAttributeFilter(newrelic.tests.test_cases.TestCase):
    def test_default_all_destinations_enabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == DST_ALL

    def test_destination_transaction_segments_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
            'transaction_segments.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_TRANSACTION_SEGMENTS)

    def test_destination_span_events_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
            'span_events.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_SPAN_EVENTS)

    def test_destination_browser_monitoring_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_BROWSER_MONITORING)

    def test_destination_error_collector_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
            'error_collector.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_ERROR_COLLECTOR)

    def test_destination_transaction_tracer_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
            'transaction_tracer.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_TRANSACTION_TRACER)

    def test_destination_transaction_events_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
            'transaction_events.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_TRANSACTION_EVENTS)

    def test_multiple_events_disabled(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
            'transaction_events.attributes.enabled': False,
            'transaction_tracer.attributes.enabled': False,
        })
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == (DST_ALL & ~DST_TRANSACTION_EVENTS & ~DST_TRANSACTION_TRACER)

    def test_cached_destination(self):
        settings = finalize_application_settings({
            'browser_monitoring.attributes.enabled': True,
        })
        settings.attribute_filter.cache['foo'] = DST_NONE
        destinations = settings.attribute_filter.apply('foo', DST_ALL)
        assert destinations == DST_NONE
