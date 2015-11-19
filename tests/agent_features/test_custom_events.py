import pytest

from newrelic.agent import background_task, record_custom_event

from testing_support.fixtures import (reset_core_stats_engine,
        validate_transaction_record_custom_event)


@reset_core_stats_engine()
@validate_transaction_record_custom_event('CustomType', {})
@background_task()
def test_custom_events_record_in_transaction():
    record_custom_event('CustomType', {})

@reset_core_stats_engine()
@validate_transaction_record_custom_event('CustomType', {1: 2, 'foo': 'bar'})
@background_task()
def test_custom_events_record_in_transaction_with_params():
    record_custom_event('CustomType', {1: 2, 'foo': 'bar'})
