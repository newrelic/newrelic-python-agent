import sys
import time
import webtest

from newrelic.agent import (record_exception, application, callable_name,
        application_settings)
from newrelic.common.encoding_utils import obfuscate, json_encode

from testing_support.fixtures import (validate_error_event_sample_data,
        validate_non_transaction_error_event, override_application_settings,
        make_cross_agent_headers, make_synthetics_header,
        reset_core_stats_engine)
from testing_support.sample_applications import fully_featured_app


# Error in test app hard-coded as a ValueError
SYNTHETICS_RESOURCE_ID = '09845779-16ef-4fa7-b7f2-44da8e62931c'
SYNTHETICS_JOB_ID = '8c7dd3ba-4933-4cbb-b1ed-b62f511782f4'
SYNTHETICS_MONITOR_ID = 'dc452ae9-1a93-4ab5-8a33-600521e9cd00'

ERR_MESSAGE = 'Transaction had bad value'
ERROR = ValueError(ERR_MESSAGE)

fully_featured_application = webtest.TestApp(fully_featured_app)

_intrinsic_attributes = {
        'error.class': callable_name(ERROR),
        'error.message': ERR_MESSAGE,
        'transactionName' : 'WebTransaction/Uri/'
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=False)
def test_transaction_error_event_no_extra_attributes():
    test_environ = {
                'err_message' : ERR_MESSAGE,
                'record_attributes': 'FALSE'
    }
    response = fully_featured_application.get('/', extra_environ=test_environ)

_intrinsic_attributes = {
        'error.class': callable_name(ERROR),
        'error.message': ERR_MESSAGE,
        'transactionName' : 'WebTransaction/Uri/',
        'databaseCallCount': 2,
        'externalCallCount': 2,
        'queueDuration': True,
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=True)
def test_transaction_error_event_lotsa_attributes():
    test_environ = {
            'err_message' : ERR_MESSAGE,
            'external' : '2',
            'db' : '2',
            'mod_wsgi.queue_start' : ('t=%r' % time.time()),
    }
    response = fully_featured_application.get('/', extra_environ=test_environ)

_intrinsic_attributes = {
        'error.class': callable_name(ERROR),
        'error.message': ERR_MESSAGE,
        'transactionName' : 'OtherTransaction/Uri/',
        'databaseCallCount': 2,
        'externalCallCount': 2,
        'queueDuration': False,
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=True)
def test_transaction_error_background_task():
    test_environ = {
            'err_message' : ERR_MESSAGE,
            'external' : '2',
            'db' : '2',
            'newrelic.set_background_task': True
    }
    response = fully_featured_application.get('/', extra_environ=test_environ)

_intrinsic_attributes = {
        'error.class': callable_name(ERROR),
        'error.message': ERR_MESSAGE,
        'transactionName' : 'WebTransaction/Uri/',
        'nr.referringTransactionGuid': 7,
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=True)
def test_transaction_error_cross_agent():
    test_environ = {
            'err_message' : ERR_MESSAGE,
    }
    settings = application_settings()
    transaction_data = [7, 1, 77, '/path-hash']
    headers = make_cross_agent_headers(transaction_data, settings.encoding_key,
            settings.cross_process_id)
    response = fully_featured_application.get('/', headers=headers,
            extra_environ=test_environ)

_intrinsic_attributes = {
        'error.class': callable_name(ERROR),
        'error.message': ERR_MESSAGE,
        'transactionName' : 'WebTransaction/Uri/',
        'nr.syntheticsResourceId' : SYNTHETICS_RESOURCE_ID,
        'nr.syntheticsJobId' : SYNTHETICS_JOB_ID,
        'nr.syntheticsMonitorId' : SYNTHETICS_MONITOR_ID,
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=True)
def test_transaction_error_with_synthetics():
    test_environ = {
            'err_message' : ERR_MESSAGE,
    }
    settings = application_settings()
    headers = make_synthetics_header(settings.trusted_account_ids[0],
                                     SYNTHETICS_RESOURCE_ID,
                                     SYNTHETICS_JOB_ID,
                                     SYNTHETICS_MONITOR_ID,
                                     settings.encoding_key)
    response = fully_featured_application.get('/', headers=headers,
            extra_environ=test_environ)

_intrinsic_attributes = {
        'error.class': callable_name(ERROR),
        'error.message': ERR_MESSAGE,
        'transactionName' : 'WebTransaction/Uri/'
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=True, num_errors=2)
def test_multiple_errors_in_transaction():
    test_environ = {
                'err_message' : ERR_MESSAGE,
                'n_errors': '2',
    }
    response = fully_featured_application.get('/', extra_environ=test_environ)

# -------------- Test Error Events outside of transaction ----------------

class ErrorEventOutsideTransactionError(Exception):
    pass
outside_error = ErrorEventOutsideTransactionError(ERR_MESSAGE)

_intrinsic_attributes = {
        'error.class': callable_name(outside_error),
        'error.message': ERR_MESSAGE,
}

@reset_core_stats_engine()
@validate_non_transaction_error_event(_intrinsic_attributes)
def test_error_event_outside_transaction():
    try:
        raise outside_error
    except ErrorEventOutsideTransactionError:
        app = application()
        record_exception(*sys.exc_info(), application=app)

