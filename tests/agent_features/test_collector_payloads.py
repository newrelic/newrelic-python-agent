import webtest

from testing_support.fixtures import (validate_error_trace_collector_json,
        validate_tt_collector_json, validate_transaction_event_collector_json,
        validate_error_event_collector_json,
        validate_custom_event_collector_json)

from testing_support.sample_applications import (simple_app,
        simple_exceptional_app, simple_custom_event_app)


exceptional_application = webtest.TestApp(simple_exceptional_app)
normal_application = webtest.TestApp(simple_app)
custom_event_application = webtest.TestApp(simple_custom_event_app)

@validate_error_trace_collector_json()
def test_error_trace_json():
    try:
        response = exceptional_application.get('/')
    except ValueError:
        pass

@validate_error_event_collector_json()
def test_error_event_json():
    try:
        response = exceptional_application.get('/')
    except ValueError:
        pass

@validate_tt_collector_json()
def test_transaction_trace_json():
    response = normal_application.get('/')

@validate_transaction_event_collector_json()
def test_transaction_event_json():
    response = normal_application.get('/')

@validate_custom_event_collector_json()
def test_custom_event_json():
    response = custom_event_application.get('/')
