from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import record_exception
from newrelic.core.config import ignore_status_code
from newrelic.common.object_wrapper import wrap_function_wrapper


def should_ignore(exc, value, tb):
    from werkzeug.exceptions import HTTPException

    # Werkzeug HTTPException can be raised internally by Flask or in
    # user code if they mix Flask with Werkzeug. Filter based on the
    # HTTP status code.

    if isinstance(value, HTTPException):
        if ignore_status_code(value.code):
            return True


def _nr_wrap_Api_handle_error_(wrapped, instance, args, kwargs):

    # If calling wrapped raises an exception, the error will bubble up to
    # flask's exception handler and we will capture it there.
    resp = wrapped(*args, **kwargs)

    record_exception(ignore_errors=should_ignore)

    return resp


def instrument_flask_rest(module):
    wrap_function_wrapper(module, 'Api.handle_error',
            _nr_wrap_Api_handle_error_)
