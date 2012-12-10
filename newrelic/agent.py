import warnings

import newrelic.core.agent
import newrelic.core.config

import newrelic.api.web_transaction
import newrelic.api.background_task

import newrelic.api.transaction
import newrelic.api.application

import newrelic.api.transaction_name

import newrelic.api.function_trace
import newrelic.api.external_trace
import newrelic.api.error_trace

import newrelic.api.in_function
import newrelic.api.out_function
import newrelic.api.post_function
import newrelic.api.pre_function

import newrelic.api.object_wrapper

import newrelic.config

initialize = newrelic.config.initialize
global_settings = newrelic.core.config.global_settings
application = newrelic.api.application.application_instance
current_transaction = newrelic.api.transaction.current_transaction

def register_application(name=None, timeout=None):
    instance = application(name)
    instance.activate(timeout)
    return instance

def shutdown_agent(timeout=None):
    agent = newrelic.core.agent.agent_instance()
    agent.shutdown_agent(timeout)

def set_transaction_name(name, group=None, priority=None):
    transaction = current_transaction()
    if transaction:
        transaction.name_transaction(name, group, priority)

def name_transaction(name, group=None, priority=None):
    #warnings.warn('API change. Use set_transaction_name() instead of '
    #        'name_transaction().', DeprecationWarning, stacklevel=2)
    transaction = current_transaction()
    if transaction:
        transaction.name_transaction(name, group, priority)

def end_of_transaction():
    transaction = current_transaction()
    if transaction:
        transaction.stop_recording()

def set_background_task(flag=True):
    transaction = current_transaction()
    if transaction:
        transaction.background_task = flag

def ignore_transaction(flag=True):
    transaction = current_transaction()
    if transaction:
        transaction.ignore_transaction = flag

def suppress_apdex_metric(flag=True):
    transaction = current_transaction()
    if transaction:
        transaction.suppress_apdex = flag

def capture_request_params(flag=True):
    transaction = current_transaction()
    if transaction:
        transaction.capture_params = flag

def add_custom_parameter(key, value):
    transaction = current_transaction()
    if transaction:
        transaction.add_custom_parameter(key, value)

def add_user_attribute(key, value):
    transaction = current_transaction()
    if transaction:
        transaction.add_user_attribute(key, value)

def record_exception(exc, value, tb, params={}, ignore_errors=[]):
    transaction = current_transaction()
    if transaction:
        transaction.record_exception(exc, value, tb, params, ignore_errors)

def record_custom_metric(name, value, application=None):
    if application is None:
        transaction = current_transaction()
        if transaction:
            transaction.record_metric(name, value)
    else:
        if application.enabled:
            application.record_metric(name, value)

def get_browser_timing_header():
    transaction = current_transaction()
    if transaction and hasattr(transaction, 'browser_timing_header'):
        return transaction.browser_timing_header()
    return ''

def get_browser_timing_footer():
    transaction = current_transaction()
    if transaction and hasattr(transaction, 'browser_timing_footer'):
        return transaction.browser_timing_footer()
    return ''

def disable_browser_autorum(flag=True):
    transaction = current_transaction()
    if transaction:
        transaction.autorum_disabled = flag

def suppress_transaction_trace(flag=True):
    transaction = current_transaction()
    if transaction:
        transaction.suppress_transaction_trace = flag

wsgi_application = newrelic.api.web_transaction.wsgi_application
WebTransaction = newrelic.api.web_transaction.WebTransaction
WSGIApplicationWrapper = newrelic.api.web_transaction.WSGIApplicationWrapper
wrap_wsgi_application = newrelic.api.web_transaction.wrap_wsgi_application

background_task = newrelic.api.background_task.background_task
BackgroundTask = newrelic.api.background_task.BackgroundTask
BackgroundTaskWrapper = newrelic.api.background_task.BackgroundTaskWrapper
wrap_background_task = newrelic.api.background_task.wrap_background_task

function_trace = newrelic.api.function_trace.function_trace
FunctionTrace = newrelic.api.function_trace.FunctionTrace
FunctionTraceWrapper = newrelic.api.function_trace.FunctionTraceWrapper
wrap_function_trace = newrelic.api.function_trace.wrap_function_trace

external_trace = newrelic.api.external_trace.external_trace
ExternalTrace = newrelic.api.external_trace.ExternalTrace
ExternalTraceWrapper = newrelic.api.external_trace.ExternalTraceWrapper
wrap_external_trace = newrelic.api.external_trace.wrap_external_trace

error_trace = newrelic.api.error_trace.error_trace
ErrorTrace = newrelic.api.error_trace.ErrorTrace
ErrorTraceWrapper = newrelic.api.error_trace.ErrorTraceWrapper
wrap_error_trace = newrelic.api.error_trace.wrap_error_trace

transaction_name = newrelic.api.transaction_name.transaction_name
TransactionNameWrapper = newrelic.api.transaction_name.TransactionNameWrapper
wrap_transaction_name = newrelic.api.transaction_name.wrap_transaction_name

ObjectWrapper = newrelic.api.object_wrapper.ObjectWrapper
callable_name = newrelic.api.object_wrapper.callable_name
wrap_object = newrelic.api.object_wrapper.wrap_object

in_function = newrelic.api.in_function.in_function
InFunctionWrapper = newrelic.api.in_function.InFunctionWrapper
wrap_in_function = newrelic.api.in_function.wrap_in_function

out_function = newrelic.api.out_function.out_function
OutFunctionWrapper = newrelic.api.out_function.OutFunctionWrapper
wrap_out_function = newrelic.api.out_function.wrap_out_function

post_function = newrelic.api.post_function.post_function
PostFunctionWrapper = newrelic.api.post_function.PostFunctionWrapper
wrap_post_function = newrelic.api.post_function.wrap_post_function

pre_function = newrelic.api.pre_function.pre_function
PreFunctionWrapper = newrelic.api.pre_function.PreFunctionWrapper
wrap_pre_function = newrelic.api.pre_function.wrap_pre_function
