import sys
import time

from newrelic.agent import (record_exception, application, callable_name)

from testing_support.fixtures import (validate_error_event_sample_data,
        validate_non_transaction_error_event)
from testing_support.test_applications import (target_application,
        user_attributes_added)

# Error in test app hard-coded as a ValueError

ERR_MESSAGE = 'Transaction had bad value'
ERROR = ValueError(ERR_MESSAGE)

_user_attributes = user_attributes_added()

_intrinsic_attributes = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/'
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes)
def test_transaction_error_event_no_extra_attributes():
    test_environ = {
                'err_message' : ERR_MESSAGE,
                'record_attributes': 'FALSE'
    }
    response = target_application.get('/', extra_environ=test_environ)

_intrinsic_attributes = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'WebTransaction/Uri/',
    'databaseCallCount': 2,
    'externalCallCount': 2,
    'queueDuration': True,
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
def test_transaction_error_event_lotsa_attributes():
    test_environ = {
                'err_message' : ERR_MESSAGE,
                'external' : '2',
                'db' : '2',
                'mod_wsgi.queue_start' : ('t=%r' % time.time()),
    }
    response = target_application.get('/', extra_environ=test_environ)

_intrinsic_attributes = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
    'transactionName' : 'OtherTransaction/Uri/',
    'databaseCallCount': 2,
    'externalCallCount': 2,
    'queueDuration': False,
}

@validate_error_event_sample_data(required_attrs=_intrinsic_attributes,
        required_user_attrs=_user_attributes)
def test_transaction_error_background_task():
    test_environ = {
                'err_message' : ERR_MESSAGE,
                'external' : '2',
                'db' : '2',
                'newrelic.set_background_task': True
    }
    response = target_application.get('/', extra_environ=test_environ)

# -------------- Test Error Events outside of transaction ----------------

ERR_MESSAGE = 'Transaction had bad value'
ERROR = ValueError(ERR_MESSAGE)

_intrinsic_attributes = {
    'error.class': callable_name(ERROR),
    'error.message': ERR_MESSAGE,
}

@validate_non_transaction_error_event(_intrinsic_attributes)
def test_error_event_outside_transaction():
    try:
        raise ERROR
    except ValueError:
        app = application()
        record_exception(*sys.exc_info(), application=app)

