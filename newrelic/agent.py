from newrelic.config import initialize, extra_settings
from newrelic.core.config import global_settings, ignore_status_code

from newrelic.core.agent import shutdown_agent, register_data_source

from newrelic.samplers.decorators import (data_source_generator,
        data_source_factory)

from newrelic.api.application import (application_instance as application,
        register_application, application_settings)

from newrelic.api.transaction import (current_transaction,
        set_transaction_name, end_of_transaction, set_background_task,
        ignore_transaction, suppress_apdex_metric, capture_request_params,
        add_custom_parameter, add_framework_info, record_exception,
        get_browser_timing_header, get_browser_timing_footer,
        disable_browser_autorum, suppress_transaction_trace,
        record_custom_metric, record_custom_metrics, record_custom_event)

# DEPRECATED - The name_transaction() call is deprecated and the
# set_transaction_name() function should be used instead.

from newrelic.api.transaction import name_transaction

# DEPRECATED - The add_user_attribute() call is deprecated and the
# add_custom_parameter() function should be used instead.

from newrelic.api.transaction import add_user_attribute

from newrelic.api.web_transaction import (wsgi_application, WebTransaction,
        WSGIApplicationWrapper, wrap_wsgi_application)

from newrelic.api.background_task import (background_task, BackgroundTask,
        BackgroundTaskWrapper, wrap_background_task)

from newrelic.api.transaction_name import (transaction_name,
        TransactionNameWrapper, wrap_transaction_name)

from newrelic.api.function_trace import (function_trace, FunctionTrace,
        FunctionTraceWrapper, wrap_function_trace)

# EXPERIMENTAL - Generator traces are currently experimental and may not
# exist in this form in future versions of the agent.

from newrelic.api.generator_trace import (generator_trace,
        GeneratorTraceWrapper, wrap_generator_trace)

# EXPERIMENTAL - Profile traces are currently experimental and may not
# exist in this form in future versions of the agent.

from newrelic.api.profile_trace import (profile_trace, ProfileTraceWrapper,
        wrap_profile_trace)

from newrelic.api.database_trace import (database_trace, DatabaseTrace,
        DatabaseTraceWrapper, wrap_database_trace, register_database_client)

from newrelic.api.datastore_trace import (datastore_trace, DatastoreTrace,
        DatastoreTraceWrapper, wrap_datastore_trace)

from newrelic.api.external_trace import (external_trace, ExternalTrace,
        ExternalTraceWrapper, wrap_external_trace)

from newrelic.api.error_trace import (error_trace, ErrorTrace,
        ErrorTraceWrapper, wrap_error_trace)

from newrelic.common.object_names import callable_name

from newrelic.common.object_wrapper import (ObjectProxy, wrap_object,
        wrap_object_attribute, resolve_path, transient_function_wrapper,
        FunctionWrapper, function_wrapper, wrap_function_wrapper,
        patch_function_wrapper, ObjectWrapper, wrap_callable,
        pre_function, PreFunctionWrapper, wrap_pre_function,
        post_function, PostFunctionWrapper, wrap_post_function,
        in_function, InFunctionWrapper, wrap_in_function,
        out_function, OutFunctionWrapper, wrap_out_function)

from newrelic.api.html_insertion import (insert_html_snippet,
        verify_body_exists)
