import os

import newrelic.core.agent
import newrelic.core.config

import newrelic.api.web_transaction
import newrelic.api.background_task

import newrelic.api.transaction
import newrelic.api.application

import newrelic.api.function_trace

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

def name_transaction(name, group=None, priority=None):
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

def record_custom_metric(name, value):
    transaction = current_transaction()
    if transaction:
        transaction.record_metric(name, value)

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

background_task = newrelic.api.background_task.background_task
BackgroundTask = newrelic.api.background_task.BackgroundTask
BackgroundTaskWrapper = newrelic.api.background_task.BackgroundTaskWrapper

function_trace = newrelic.api.function_trace.function_trace
FunctionTrace = newrelic.api.function_trace.FunctionTrace
FunctionTraceWrapper = newrelic.api.function_trace.FunctionTraceWrapper
