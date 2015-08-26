import webtest

from testing_support.fixtures import (override_application_settings,
        validate_transaction_error_trace_attributes,
        core_application_stats_engine_error, check_error_attributes)

from newrelic.agent import (application, callable_name, wsgi_application,
        add_custom_parameter)

URL_PARAM = 'some_key'
URL_PARAM_VAL = 'some_value'
REQUEST_URL = '/?'+ URL_PARAM + '=' + URL_PARAM_VAL
REQUEST_HEADERS = [('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', '10'),]

DEFAULT_AGENT_KEYS = ['wsgi.output.time', 'response.status', 'request.method',
        'request.headers.content-type', 'request.headers.content-length']
AGENT_KEYS_REQ_PARAM = DEFAULT_AGENT_KEYS + ['request.parameters.'+URL_PARAM]


@wsgi_application()
def target_wsgi_application(environ, start_response):

    add_custom_parameter('test_key', 'test_value')

    start_response('500 :(',[])

    raise ValueError('Transaction had bad value')

target_application = webtest.TestApp(target_wsgi_application)

def run_failing_request():
    try:
        response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)
    except ValueError:
        pass


# ===== Tests for checking the presence and format of agent attributes ========
# =============================================================================

# ========================= default settings

_expected_attributes = {
        'agent' : DEFAULT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

_expected_absent_attributes = {
        'agent' : ['request.parameters.'+URL_PARAM],
        'user' : [],
}


@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings({})
def test_error_in_transaction_trace_default_settings():
    run_failing_request()

# ========================= include all

_override_settings = {
        'error_collector.attributes.include': ['request.parameters.*'],
}

_expected_attributes = {
        'agent' : AGENT_KEYS_REQ_PARAM,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_trace_include_all():
    run_failing_request()

# ========================= include and exclude

_override_settings = {
        'error_collector.attributes.exclude': ['request.parameters.*'],
        'error_collector.attributes.include': ['request.parameters.'+URL_PARAM],
}

_expected_attributes = {
        'agent' : AGENT_KEYS_REQ_PARAM,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_trace_include_exclude():
    run_failing_request()

# ========================= capture_params

_override_settings = {
        'capture_params': True,
}

_expected_attributes = {
        'agent' : AGENT_KEYS_REQ_PARAM,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}


@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_trace_deprecated_capture_params_true():
    run_failing_request()

_override_settings = {
        'capture_params': False,
}

_expected_attributes = {
        'agent' : DEFAULT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

_expected_absent_attributes = {
        'agent' : ['request.parameters.'+URL_PARAM],
        'user' : [],
}

@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_trace_deprecated_capture_params_false():
    run_failing_request()


# ========================= attempt to override intrinsic

_override_settings = {
        'attributes.error_collector.exclude': ['trip_id'],
}

_expected_attributes = {
        'agent' : DEFAULT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_trace_exclude_intrinsic():
    run_failing_request()

# =========================  attributes off

_override_settings = {
        'error_collector.attributes.enabled' : False
}

_expected_attributes = {
        'user' : [],
        'agent' : [],
        'intrinsic' : ['trip_id']
}

_expected_absent_attributes = {
        'agent' : AGENT_KEYS_REQ_PARAM,
        'user' : ['test_key'],
}

@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_in_transaction_trace_attributes_disabled():
    run_failing_request()
