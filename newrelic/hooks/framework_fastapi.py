from copy import copy
from newrelic.api.time_trace import current_trace
from newrelic.api.function_trace import FunctionTraceWrapper
from newrelic.common.object_wrapper import wrap_function_wrapper, function_wrapper
from newrelic.common.object_names import callable_name
from newrelic.core.trace_cache import trace_cache


def use_context(trace):

    @function_wrapper
    def context_wrapper(wrapped, instance, args, kwargs):
        cache = trace_cache()
        thread_id = cache.thread_start(trace)
        try:
            return wrapped(*args, **kwargs)
        finally:
            cache.thread_stop(thread_id)

    return context_wrapper


def wrap_run_endpoint_function(wrapped, instance, args, kwargs):
    trace = current_trace()
    if trace and trace.transaction:
        dependant = kwargs["dependant"]
        name = callable_name(dependant.call)
        trace.transaction.set_transaction_name(name)

        if not kwargs["is_coroutine"]:
            dependant = kwargs["dependant"] = copy(dependant)
            dependant.call = use_context(trace)(FunctionTraceWrapper(dependant.call))
            return wrapped(*args, **kwargs)
        else:
            return FunctionTraceWrapper(wrapped, name=name)(*args, **kwargs)

    return wrapped(*args, **kwargs)


def instrument_fastapi_routing(module):
    if hasattr(module, "run_endpoint_function"):
        wrap_function_wrapper(module, "run_endpoint_function", wrap_run_endpoint_function)
