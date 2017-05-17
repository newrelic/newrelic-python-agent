from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.core.agent import agent_instance
from newrelic.core.config import global_settings


_methods = [
    'initialize', 'extra_settings', 'global_settings', 'ignore_status_code',
    'shutdown_agent', 'register_data_source', 'data_source_generator',
    'data_source_factory', 'application', 'register_application',
    'application_settings', 'current_transaction', 'set_transaction_name',
    'end_of_transaction', 'set_background_task', 'ignore_transaction',
    'suppress_apdex_metric', 'capture_request_params', 'add_custom_parameter',
    'add_framework_info', 'record_exception', 'get_browser_timing_header',
    'get_browser_timing_footer', 'disable_browser_autorum',
    'suppress_transaction_trace', 'record_custom_metric',
    'record_custom_metrics', 'record_custom_event', 'name_transaction',
    'add_user_attribute', 'wsgi_application', 'WebTransaction',
    'WSGIApplicationWrapper', 'wrap_wsgi_application', 'background_task',
    'BackgroundTask', 'BackgroundTaskWrapper', 'wrap_background_task',
    'transaction_name', 'TransactionNameWrapper', 'wrap_transaction_name',
    'function_trace', 'FunctionTrace', 'FunctionTraceWrapper',
    'wrap_function_trace', 'generator_trace', 'GeneratorTraceWrapper',
    'wrap_generator_trace', 'profile_trace', 'ProfileTraceWrapper',
    'wrap_profile_trace', 'database_trace', 'DatabaseTrace',
    'DatabaseTraceWrapper', 'wrap_database_trace', 'register_database_client',
    'datastore_trace', 'DatastoreTrace', 'DatastoreTraceWrapper',
    'wrap_datastore_trace', 'external_trace', 'ExternalTrace',
    'ExternalTraceWrapper', 'wrap_external_trace', 'error_trace', 'ErrorTrace',
    'ErrorTraceWrapper', 'wrap_error_trace', 'callable_name', 'ObjectProxy',
    'wrap_object', 'wrap_object_attribute', 'resolve_path',
    'transient_function_wrapper', 'FunctionWrapper', 'function_wrapper',
    'wrap_function_wrapper', 'patch_function_wrapper', 'ObjectWrapper',
    'wrap_callable', 'pre_function', 'PreFunctionWrapper', 'wrap_pre_function',
    'post_function', 'PostFunctionWrapper', 'wrap_post_function',
    'in_function', 'InFunctionWrapper', 'wrap_in_function', 'out_function',
    'OutFunctionWrapper', 'wrap_out_function', 'insert_html_snippet',
    'verify_body_exists',
]


def _wrap_api_call(module, method):

    agent = agent_instance()
    app_name = global_settings().app_name
    metric_name = 'Supportability/api/%s' % method

    def _nr_wrap_newrelic_agent_(wrapped, instance, args, kwargs):

        transaction = current_transaction()

        if transaction:
            transaction._transaction_metrics[metric_name] = (
                transaction._transaction_metrics.setdefault(metric_name, 0) + 1)
        else:
            agent.record_custom_metric(app_name, metric_name, {'count': 1})

        return wrapped(*args, **kwargs)

    wrap_function_wrapper(module, method, _nr_wrap_newrelic_agent_)


def instrument_newrelic_agent(module):
    for method in _methods:
        if hasattr(module, method):
            _wrap_api_call(module, method)
