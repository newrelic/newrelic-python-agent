import webtest

from newrelic.agent import wsgi_application, add_custom_parameter

from testing_support.fixtures import (validate_transaction_trace_attributes,
        override_application_settings)


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
    status = '200 OK'

    output = '<html><head>header</head><body><p>RESPONSE</p></body></html>'
    output = output.encode('UTF-8')

    add_custom_parameter('test_key', 'test_value')

    response_headers = [('Content-Type', 'text/html; charset=utf-8'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]

target_application = webtest.TestApp(target_wsgi_application)

# ========================= default settings

_override_settings = {}

_expected_attributes = {
        'agent' : DEFAULT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

_expected_absent_attributes = {
        'agent' : ['request.parameters.'+URL_PARAM],
        'user' : [],
}

@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_default_attribute_settings():
    response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= include request params

_override_settings = {
        'transaction_tracer.attributes.include': ['request.parameters.*'],
}

_expected_attributes = {
        'agent' : AGENT_KEYS_REQ_PARAM,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_default_request_parameters_attributes():
    response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

# ========================= capture_params

_override_settings = {
        'capture_params': True,
}

_expected_attributes = {
        'agent' : AGENT_KEYS_REQ_PARAM,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_deprecated_capture_params_true():
    response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


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

@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_deprecated_capture_params_false():
    response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# ========================= attempt to override intrinsic

_override_settings = {
        'attributes.transaction_tracer.exclude': ['trip_id'],
}

_expected_attributes = {
        'agent' : DEFAULT_AGENT_KEYS,
        'user' : ['test_key'],
        'intrinsic' : ['trip_id']
}

@validate_transaction_trace_attributes(_expected_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_exclude_intrinsic():
    response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)


# =========================  attributes off

_override_settings = {
        'transaction_tracer.attributes.enabled' : False
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

@validate_transaction_trace_attributes(_expected_attributes,
        _expected_absent_attributes)
@override_application_settings(_override_settings)
def test_transaction_trace_attributes_disabled():
    response = target_application.get(REQUEST_URL, headers=REQUEST_HEADERS)

