import webtest

from newrelic.agent import (application, callable_name,
        wsgi_application, add_custom_parameter)

from testing_support.fixtures import (validate_transaction_trace_attributes,
        validate_transaction_error_trace_attributes,
        override_application_settings, core_application_stats_engine_error,
        check_error_attributes, validate_transaction_event_attributes,
        validate_browser_attributes)


URL_PARAM = 'some_key'
URL_PARAM_VAL = 'some_value'
REQUEST_URL = '/?'+ URL_PARAM + '=' + URL_PARAM_VAL
REQUEST_HEADERS = [('Content-Type', 'text/html; charset=utf-8'),
        ('Content-Length', '10'),]

TRACE_ERROR_AGENT_KEYS = ['wsgi.output.time', 'response.status', 'request.method',
        'request.headers.content-type', 'request.headers.content-length']
AGENT_KEYS_ALL = TRACE_ERROR_AGENT_KEYS + ['request.parameters.'+URL_PARAM]

EVENT_INTRINSICS = ('name', 'duration', 'type', 'timestamp')
EVENT_AGENT_KEYS = ['response.status', 'request.method',
        'request.headers.content-type', 'request.headers.content-length']

BROWSER_INTRINSIC_KEYS = ["beacon", "errorBeacon", "licenseKey", "applicationID",
        "transactionName", "queueTime", "applicationTime", "agent"]
BROWSER_AGENT_KEYS = ['request.method', 'request.headers.content-type',
        'request.headers.content-length']

@wsgi_application()
def exceptional_wsgi_application(environ, start_response):

    add_custom_parameter('test_key', 'test_value')

    start_response('500 :(',[])

    raise ValueError('Transaction had bad value')

@wsgi_application()
def normal_wsgi_application(environ, start_response):
    status = '200 OK'

    output = '<html><head>header</head><body><p>RESPONSE</p></body></html>'
    output = output.encode('UTF-8')

    add_custom_parameter('test_key', 'test_value')

    response_headers = [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

exceptional_application = webtest.TestApp(exceptional_wsgi_application)
normal_application = webtest.TestApp(normal_wsgi_application)

def run_failing_request():
    try:
        response = exceptional_application.get(REQUEST_URL, headers=REQUEST_HEADERS)
    except ValueError:
        pass

# ===== Tests for checking the presence and format of agent attributes ========
# =============================================================================

# ========================= default settings

_expected_attributes = {
        'agent' : TRACE_ERROR_AGENT_KEYS,
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
def test_error_trace_in_transaction_default_settings():
    run_failing_request()

@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings({})
def test_transaction_trace_default_attribute_settings():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_expected_attributes = {
        'agent' : EVENT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : ['wsgi.output.time'],
        'user' : [],
}

@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings({})
def test_transaction_event_default_attribute_settings():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# Browser monitoring off by default

_override_settings = {
        'browser_monitoring.attributes.enabled' : True,
}

_expected_attributes = {
        'agent' : [],
        'user' : ['test_key'],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS,
        'user' : ['test_key'],
}

@validate_browser_attributes(_expected_attributes, {})
@override_application_settings(_override_settings)
def test_browser_default_attribute_settings():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= include request params

_override_settings = {
        'error_collector.attributes.include': ['request.parameters.*'],
}

_expected_attributes = {
        'agent' : AGENT_KEYS_ALL,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_trace_in_transaction_include_request_params():
    run_failing_request()

_override_settings = {
        'transaction_tracer.attributes.include': ['request.parameters.*'],
}

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_include_request_params():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'transaction_events.attributes.include': ['request.parameters.*'],
}

_expected_attributes = {
        'agent' : EVENT_AGENT_KEYS + ['request.parameters.'+URL_PARAM],
        'user' : ['test_key'],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : ['wsgi.output.time'],
        'user' : [],
}

@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_include_request_params():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_override_settings = {
        'browser_monitoring.attributes.enabled' : True,
        'browser_monitoring.attributes.include': ['request.parameters.*'],
}

_expected_attributes = {
        'agent' : ['request.parameters.'+URL_PARAM],
        'user' : ['test_key'],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS,
        'user' : ['test_key'],
}

@validate_browser_attributes(_expected_attributes, {})
@override_application_settings(_override_settings)
def test_browser_include_request_params():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= include and exclude

_override_settings = {
        'error_collector.attributes.exclude': ['request.parameters.*'],
        'error_collector.attributes.include': ['request.parameters.'+URL_PARAM],
}

_expected_attributes = {
        'agent' : AGENT_KEYS_ALL,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_trace_in_transaction_include_exclude():
    run_failing_request()

_override_settings = {
        'transaction_tracer.attributes.exclude': ['request.parameters.*'],
        'transaction_tracer.attributes.include': ['request.parameters.'+URL_PARAM],
}

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_include_exclude():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_override_settings = {
        'transaction_events.attributes.exclude': ['request.parameters.*'],
        'transaction_events.attributes.include': ['*', 'request.parameters.'+URL_PARAM],
}

_expected_attributes = {
        'agent' : AGENT_KEYS_ALL,
        'user' : ['test_key'],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : [],
        'user' : [],
}

@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_include_exclude():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'browser_monitoring.attributes.enabled' : True,
        'transaction_tracer.attributes.exclude': ['test_key'],
        'browser_monitoring.attributes.include': ['*'],
}

_expected_attributes = {
        'agent' : BROWSER_AGENT_KEYS + ['request.parameters.'+URL_PARAM],
        'user' : [],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS,
        'user' : ['test_key'],
}

@validate_browser_attributes(_expected_attributes, {})
@override_application_settings(_override_settings)
def test_browser_include_request_params():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= capture_params True

_override_settings = {
        'capture_params': True,
}

_expected_attributes = {
        'agent' : AGENT_KEYS_ALL,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_trace_in_transaction_deprecated_capture_params_true():
    run_failing_request()

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_deprecated_capture_params_true():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# capture_params should not affect transaction events or browser

_expected_attributes = {
        'agent' : EVENT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : ['wsgi.output.time', 'request.parameters.'+URL_PARAM],
        'user' : [],
}

@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_deprecated_capture_params_true():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_override_settings = {
        'browser_monitoring.attributes.enabled' : True,
        'capture_params': True,
}

_expected_attributes = {
        'agent' : [],
        'user' : ['test_key'],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS + ['request.parameters.'+URL_PARAM],
        'user' : [],
}

@validate_browser_attributes({}, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_deprecated_capture_params_true():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= capture_params False

_override_settings = {
        'capture_params': False,
}

_expected_attributes = {
        'agent' : TRACE_ERROR_AGENT_KEYS,
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
def test_error_trace_in_transaction_deprecated_capture_params_false():
    run_failing_request()


@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_deprecated_capture_params_false():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# capture_params should not affect transaction events

_expected_attributes = {
        'agent' : EVENT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : ['wsgi.output.time'],
        'user' : [],
}

@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_deprecated_capture_params_false():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_override_settings = {
        'browser_monitoring.attributes.enabled' : True,
        'capture_params': False,
}

_expected_attributes = {
        'agent' : [],
        'user' : ['test_key'],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS + ['request.parameters.'+URL_PARAM],
        'user' : [],
}

@validate_browser_attributes({}, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_deprecated_capture_params_false():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= attempt to exclude intrinsic

_override_settings = {
        'error_collector.attributes.exclude': ['trip_id'],
}

_expected_attributes = {
        'agent' : TRACE_ERROR_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_error_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_error_trace_in_transaction_exclude_intrinsic():
    run_failing_request()

_override_settings = {
        'transaction_tracer.attributes.exclude': ['trip_id'],
}

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_exclude_intrinsic():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


_override_settings = {
        'transaction_events.attributes.exclude': ['name', 'duration',
            'timestamp', 'type'],
}

_expected_attributes = {
        'agent' : EVENT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : ['wsgi.output.time'],
        'user' : [],
}

@validate_transaction_event_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_exclude_intrinsic():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_override_settings = {
        'browser_monitoring.attributes.enabled' : True,
        'browser_monitoring.attributes.exclude': BROWSER_INTRINSIC_KEYS,
}

_expected_attributes = {
        'agent' : [],
        'user' : ['test_key'],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS + ['request.parameters.'+URL_PARAM],
        'user' : [],
}

@validate_browser_attributes({}, _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_browser_deprecated_capture_params_false():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

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
        'agent' : AGENT_KEYS_ALL,
        'user' : ['test_key'],
}

@validate_transaction_error_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_error_trace_in_transaction_attributes_disabled():
    run_failing_request()

_override_settings = {
        'transaction_tracer.attributes.enabled' : False
}

@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_attributes_disabled():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

_override_settings = {
        'transaction_events.attributes.enabled' : False
}

_expected_attributes = {
        'user' : [],
        'agent' : [],
        'intrinsic' : EVENT_INTRINSICS
}

_expected_absent_attributes = {
        'agent' : AGENT_KEYS_ALL,
        'user' : ['test_key'],
}

@validate_transaction_event_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_event_attributes_disabled():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# Browser monitoring off by default

_expected_attributes = {
        'agent' : [],
        'user' : [],
        'intrinsic' : BROWSER_INTRINSIC_KEYS,
}

_expected_absent_attributes = {
        'agent' : BROWSER_AGENT_KEYS,
        'user' : ['test_key'],
}

@validate_browser_attributes({}, _expected_absent_attributes)
@override_application_settings({})
def test_browser_attributes_disabled():
    response = normal_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# =========================  outside transaction (error trace only)

class OutsideWithParamsError(Exception):
    pass
OutsideWithParamsError.name = callable_name(OutsideWithParamsError)

def test_error_trace_outside_transaction():

    _expected_attributes = {
            'user' : ['test_key'],
            'agent' : [],
            'intrinsic' : []
            }

    try:
        raise OutsideWithParamsError("Error outside transaction")
    except OutsideWithParamsError:
        application_instance = application()
        application_instance.record_exception(params={'test_key': 'test_value'})

    my_error = core_application_stats_engine_error(OutsideWithParamsError.name)

    check_error_attributes(my_error.parameters, _expected_attributes,
            is_transaction=False)


class OutsideNoParamsError(Exception):
    pass
OutsideNoParamsError.name = callable_name(OutsideNoParamsError)

_override_settings = {
        'error_collector.attributes.exclude' : ['test_key']
}

@override_application_settings(_override_settings)
def test_error_trace_outside_transaction_excluded_user_param():

    _expected_attributes = {}

    _expected_absent_attributes = {
            'user' : ['test_key'],
            'agent' : [],
            'intrinsic' : []
            }

    try:
        raise OutsideNoParamsError("Error outside transaction")
    except OutsideNoParamsError:
        application_instance = application()
        application_instance.record_exception(params={'test_key': 'test_value'})

    my_error = core_application_stats_engine_error(OutsideNoParamsError.name)

    check_error_attributes(my_error.parameters, _expected_attributes,
            _expected_absent_attributes, is_transaction=False)