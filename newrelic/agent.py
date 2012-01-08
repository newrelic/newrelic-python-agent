import os

import newrelic.api.web_transaction
import newrelic.api.background_task

import newrelic.api.transaction
import newrelic.api.application

import newrelic.api.function_trace

import newrelic.config

initialize = newrelic.config.initialize

def register_application(name=None, timeout=0.0):
    application = newrelic.api.application.application(name)
    application.activate(timeout)

def current_transaction():
    return newrelic.api.transaction.transaction()

def name_transaction(name, group=None, priority=None):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.name_transaction(name, group, priority)

def end_of_transaction():
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.stop_recording()

def set_background_task(flag=True):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.background_task = flag

def ignore_transaction(flag=True):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.ignore_transaction = flag

def suppress_apdex_metric(flag=True):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.suppress_apdex = flag

def capture_request_params(flag=True):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.capture_params = flag

def add_custom_parameter(key, value):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.add_custom_parameter(key, value)
    
def record_exception(exc, value, tb, params={}, ignore_errors=[]):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.notice_error(exc, value, tb, params, ignore_errors)

def record_custom_metric(name, value):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.record_metric(name, value)

def get_browser_timing_header():
    transaction = newrelic.api.transaction.transaction()
    if transaction and hasattr(transaction, 'browser_timing_header'):
        return transaction.browser_timing_header()
    return ''

def get_browser_timing_footer():
    transaction = newrelic.api.transaction.transaction()
    if transaction and hasattr(transaction, 'browser_timing_footer'):
        return transaction.browser_timing_footer()
    return ''

def disable_browser_autorum(flag=True):
    transaction = newrelic.api.transaction.transaction()
    if transaction:
        transaction.autorum_disabled = flag

wsgi_application = newrelic.api.web_transaction.wsgi_application
WSGIApplicationWrapper = newrelic.api.web_transaction.WSGIApplicationWrapper

background_task = newrelic.api.background_task.background_task
BackgroundTaskWrapper = newrelic.api.background_task.BackgroundTaskWrapper

function_trace = newrelic.api.function_trace.function_trace
FunctionTrace = newrelic.api.function_trace.FunctionTrace
FunctionTraceWrapper = newrelic.api.function_trace.FunctionTraceWrapper
