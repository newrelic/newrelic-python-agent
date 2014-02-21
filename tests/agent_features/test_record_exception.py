import sys

from testing_support.fixtures import validate_transaction_errors

from newrelic.agent import background_task, record_exception

_runtime_error_name = (RuntimeError.__module__ + ':' + RuntimeError.__name__)

_test_record_exception_sys_exc_info = [
        (_runtime_error_name, 'one')]

@validate_transaction_errors(errors=_test_record_exception_sys_exc_info)
@background_task()
def test_record_exception_sys_exc_info():
    try: 
      raise RuntimeError('one') 
    except RuntimeError: 
      record_exception(*sys.exc_info())

_test_record_exception_no_exc_info = [
        (_runtime_error_name, 'one')]

@validate_transaction_errors(errors=_test_record_exception_no_exc_info)
@background_task()
def test_record_exception_no_exc_info():
    try: 
      raise RuntimeError('one') 
    except RuntimeError: 
      record_exception()

_test_record_exception_multiple_errors = [
        (_runtime_error_name, 'one'),
        (_runtime_error_name, 'two')]

@validate_transaction_errors(errors=_test_record_exception_multiple_errors)
@background_task()
def test_record_exception_multiple():
    try: 
      raise RuntimeError('one') 
    except RuntimeError: 
      record_exception()

    try: 
      raise RuntimeError('two') 
    except RuntimeError: 
      record_exception()
