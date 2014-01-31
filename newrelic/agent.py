import warnings

import newrelic.samplers.decorators

import newrelic.core.agent
import newrelic.core.config

import newrelic.api.web_transaction

import newrelic.api.transaction
import newrelic.api.application

import newrelic.config

initialize = newrelic.config.initialize
application = newrelic.api.application.application_instance
current_transaction = newrelic.api.transaction.current_transaction

from newrelic.core.config import global_settings, ignore_status_code

def register_application(name=None, timeout=None):
    instance = application(name)
    instance.activate(timeout)
    return instance

def shutdown_agent(timeout=None):
    agent = newrelic.core.agent.agent_instance()
    agent.shutdown_agent(timeout)

def application_settings(name=None):
    instance = application(name)
    return instance.settings

def set_transaction_name(name, group=None, priority=None):
    transaction = current_transaction()
    if transaction:
        transaction.set_transaction_name(name, group, priority)

# DEPRECATED - The name_transaction() call is deprecated and the
# set_transaction_name() function should be used instead.

def name_transaction(name, group=None, priority=None):
    #warnings.warn('API change. Use set_transaction_name() instead of '
    #        'name_transaction().', DeprecationWarning, stacklevel=2)
    transaction = current_transaction()
    if transaction:
        transaction.set_transaction_name(name, group, priority)

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
    #warnings.warn('API change. Use add_custom_parameter() instead of '
    #        'add_user_attribute().', DeprecationWarning, stacklevel=2)
    return add_custom_parameter(key, value)

def record_exception(exc=None, value=None, tb=None, params={},
        ignore_errors=[]):
    transaction = current_transaction()
    if transaction:
        transaction.record_exception(exc, value, tb, params, ignore_errors)

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

def record_custom_metric(name, value, application=None):
    if application is None:
        transaction = current_transaction()
        if transaction:
            transaction.record_custom_metric(name, value)
    else:
        if application.enabled:
            application.record_custom_metric(name, value)

def record_custom_metrics(metrics, application=None):
    if application is None:
        transaction = current_transaction()
        if transaction:
            transaction.record_custom_metrics(metrics)
    else:
        if application.enabled:
            application.record_custom_metrics(metrics)

def register_data_source(source, application=None, name=None,
        settings=None, **properties):
    agent = newrelic.core.agent.agent_instance()
    agent.register_data_source(source,
            application and application.name or None, name, settings,
            **properties)

data_source_generator = newrelic.samplers.decorators.data_source_generator
data_source_factory = newrelic.samplers.decorators.data_source_factory

wsgi_application = newrelic.api.web_transaction.wsgi_application
WebTransaction = newrelic.api.web_transaction.WebTransaction
WSGIApplicationWrapper = newrelic.api.web_transaction.WSGIApplicationWrapper
wrap_wsgi_application = newrelic.api.web_transaction.wrap_wsgi_application

from .api.background_task import (background_task, BackgroundTask,
        BackgroundTaskWrapper, wrap_background_task)

from .api.function_trace import (function_trace, FunctionTrace,
        FunctionTraceWrapper, wrap_function_trace)

# EXPERIMENTAL - Generator traces are currently experimental and may not
# exist in this form in future versions of the agent.

from .api.generator_trace import (generator_trace, GeneratorTraceWrapper,
        wrap_generator_trace)

# EXPERIMENTAL - Profile traces are currently experimental and may not
# exist in this form in future versions of the agent.

from .api.profile_trace import (profile_trace, ProfileTraceWrapper,
        wrap_profile_trace)

from .api.database_trace import (database_trace, DatabaseTrace,
        DatabaseTraceWrapper, wrap_database_trace, register_database_client)

from .api.external_trace import (external_trace, ExternalTrace,
        ExternalTraceWrapper, wrap_external_trace)

from .api.error_trace import (error_trace, ErrorTrace, ErrorTraceWrapper,
        wrap_error_trace)

from .api.transaction_name import (transaction_name,
        TransactionNameWrapper, wrap_transaction_name)

from .common.object_names import callable_name

from .common.object_wrapper import (ObjectProxy, wrap_object,
        wrap_object_attribute, resolve_path, transient_function_wrapper,
        FunctionWrapper, function_wrapper, wrap_function_wrapper,
        patch_function_wrapper, ObjectWrapper, wrap_callable,
        pre_function, PreFunctionWrapper, wrap_pre_function,
	post_function, PostFunctionWrapper, wrap_post_function,
        in_function, InFunctionWrapper, wrap_in_function,
        out_function, OutFunctionWrapper, wrap_out_function)
