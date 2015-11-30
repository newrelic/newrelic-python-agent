import pytest
import time

from newrelic.agent import background_task, record_custom_event, application

from testing_support.fixtures import (reset_core_stats_engine,
        validate_transaction_record_custom_event, validate_custom_event_count,
        validate_custom_event_inside_transaction,
        validate_custom_event_outside_transaction,
        override_application_settings)


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

_now = time.time()

_intrinsic = {
    'type': 'FooEvent',
    'timestamp': _now,
}
_user_params = {'foo': 'bar'}
_event = [_intrinsic, _user_params]

@reset_core_stats_engine()
@validate_custom_event_inside_transaction(_event)
@background_task()
def test_add_custom_event_to_transaction_stats_engine():
    record_custom_event('FooEvent', _user_params)

@reset_core_stats_engine()
@validate_custom_event_outside_transaction(_event)
def test_add_custom_event_to_application_stats_engine():
    app = application()
    record_custom_event('FooEvent', _user_params, application=app)

@override_application_settings({'collect_custom_events': False})
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_settings_check_collector_flag():
    record_custom_event('FooEvent', _user_params)

@override_application_settings({'custom_insights_events.enabled': False})
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_custom_event_settings_check_custom_insights_enabled():
    record_custom_event('FooEvent', _user_params)
