# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools

from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.async_wrapper import coroutine_wrapper
from newrelic.common.object_wrapper import wrap_function_wrapper, wrap_object
from newrelic.common.signature import bind_args
from newrelic.core.context import ContextOf, context_wrapper
from newrelic.hooks.mlmodel_langchain import wrap_run_in_executor


def wrap_ToolNode__execute_tool_sync(wrapped, instance, args, kwargs):
    if not current_transaction():
        return wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        agent_name = bound_args["request"].state["messages"][-1].name
        if agent_name:
            metadata = bound_args["config"]["metadata"]
            metadata["_nr_agent_name"] = agent_name
    except Exception:
        pass

    return wrapped(*args, **kwargs)


async def wrap_ToolNode__execute_tool_async(wrapped, instance, args, kwargs):
    if not current_transaction():
        return await wrapped(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        agent_name = bound_args["request"].state["messages"][-1].name
        if agent_name:
            metadata = bound_args["config"]["metadata"]
            metadata["_nr_agent_name"] = agent_name
    except Exception:
        pass

    return await wrapped(*args, **kwargs)


def bind_submit(func, *args, **kwargs):
    return func, args, kwargs


def wrap_BackgroundExecutor_submit(wrapped):
    # We can't use wrapt FuctionWrapper here because the function will be wrapped in a weakref.WeakMethod,
    # which isn't compatible with wrapt. Instead, we have to do the wrapping manually. We use functools.wraps
    # to preserve the original function's signature, name, and annotations as best as we can.
    @functools.wraps(wrapped)
    def _wrapper(self, *args, **kwargs):
        # This will be a bound method, so the first argument must always be self.
        trace = current_trace()
        if not trace:
            return wrapped(self, *args, **kwargs)

        try:
            func, args, kwargs = bind_submit(*args, **kwargs)
        except Exception:
            return wrapped(self, *args, **kwargs)

        func = context_wrapper(func, trace=trace, strict=True)
        return wrapped(self, func, *args, **kwargs)

    return _wrapper


def wrap_AsyncBackgroundExecutor_submit(wrapped):
    # We can't use wrapt FuctionWrapper here because the function will be wrapped in a weakref.WeakMethod,
    # which isn't compatible with wrapt. Instead, we have to do the wrapping manually. We use functools.wraps
    # to preserve the original function's signature, name, and annotations as best as we can.
    @functools.wraps(wrapped)
    def _wrapper(self, *args, **kwargs):
        # This will be a bound method, so the first argument must always be self.
        trace = current_trace()
        if not trace:
            return wrapped(self, *args, **kwargs)

        try:
            func, args, kwargs = bind_submit(*args, **kwargs)
        except Exception:
            return wrapped(self, *args, **kwargs)

        context = ContextOf(trace=trace, strict=True)
        func = coroutine_wrapper(func, context)
        return wrapped(self, func, *args, **kwargs)

    return _wrapper


def _record_graph_stream_completion(instance):
    try:
        # Do not report events twice
        if getattr(instance, "_nr_closed", True):
            return

        transaction = current_transaction()
        if not transaction:
            return

        # Look for an error to report if there is one
        try:
            mux = getattr(instance, "_mux", None)
            events = getattr(mux, "_events", None) if mux is not None else None
            error = getattr(events, "_error", None) if events is not None else None
        except Exception:
            error = None

        # Mark events as reported to avoid duplicates
        instance._nr_closed = True
        if error:
            instance._nr_on_error(instance, transaction, error=error)
        else:
            instance._nr_on_stop_iteration(instance, transaction)
    except Exception:
        pass


def wrap_GraphRunStream__pump_next(wrapped, instance, args, kwargs):
    # _pump_next returns False when a graph is exhausted, either due to successful completion or a stored error.
    result = wrapped(*args, **kwargs)
    if result is False and getattr(instance, "_exhausted", False):
        _record_graph_stream_completion(instance)
    return result


async def wrap_AsyncGraphRunStream__apump_next(wrapped, instance, args, kwargs):
    # _apump_next returns False when a graph is exhausted, either due to successful completion or a stored error.
    result = await wrapped(*args, **kwargs)
    if result is False and getattr(instance, "_exhausted", False):
        _record_graph_stream_completion(instance)
    return result


def wrap_GraphRunStream_abort(wrapped, instance, args, kwargs):
    # abort is an early exit that can be called directly or by __exit__ on the context manager.
    # If the run is aborted before we record events, make one last attempt.
    result = wrapped(*args, **kwargs)
    _record_graph_stream_completion(instance)
    return result


async def wrap_AsyncGraphRunStream_abort(wrapped, instance, args, kwargs):
    # abort is an early exit that can be called directly or by __exit__ on the context manager.
    # If the run is aborted before we record events, make one last attempt.
    result = await wrapped(*args, **kwargs)
    _record_graph_stream_completion(instance)
    return result


def instrument_langgraph_prebuilt_tool_node(module):
    if hasattr(module, "ToolNode"):
        if hasattr(module.ToolNode, "_execute_tool_sync"):
            wrap_function_wrapper(module, "ToolNode._execute_tool_sync", wrap_ToolNode__execute_tool_sync)
        if hasattr(module.ToolNode, "_execute_tool_async"):
            wrap_function_wrapper(module, "ToolNode._execute_tool_async", wrap_ToolNode__execute_tool_async)


def instrument_langgraph_pregel_executor(module):
    if hasattr(module, "BackgroundExecutor"):
        wrap_object(module, "BackgroundExecutor.submit", wrap_BackgroundExecutor_submit)

    if hasattr(module, "AsyncBackgroundExecutor"):
        wrap_object(module, "AsyncBackgroundExecutor.submit", wrap_AsyncBackgroundExecutor_submit)


def instrument_langgraph_stream_run_stream(module):
    if hasattr(module, "GraphRunStream"):
        if hasattr(module.GraphRunStream, "_pump_next"):
            wrap_function_wrapper(module, "GraphRunStream._pump_next", wrap_GraphRunStream__pump_next)
        if hasattr(module.GraphRunStream, "abort"):
            wrap_function_wrapper(module, "GraphRunStream.abort", wrap_GraphRunStream_abort)
    if hasattr(module, "AsyncGraphRunStream"):
        if hasattr(module.AsyncGraphRunStream, "_apump_next"):
            wrap_function_wrapper(module, "AsyncGraphRunStream._apump_next", wrap_AsyncGraphRunStream__apump_next)
        if hasattr(module.AsyncGraphRunStream, "abort"):
            wrap_function_wrapper(module, "AsyncGraphRunStream.abort", wrap_AsyncGraphRunStream_abort)


def instrument_langgraph_internal_runnable(module):
    # langgraph._internal._runnable imports run_in_executor via `from ... import`,
    # binding the reference at import time. If that import happened before newrelic
    # hooks registered, langgraph's local reference is the unwrapped original.
    #
    # The real fix for this issue is to get users to initialize the agent correctly
    # before any imports, or to use the newrelic-admin wrapper. As a last ditch effort,
    # wrap the reference on this module so that the wrapped version is picked up at
    # compile time on StateGraph. This will only work if newrelic is initialized before
    # the StateGraph is compiled, but it should provide slightly better compatibility.
    if hasattr(module, "run_in_executor") and not hasattr(module.run_in_executor, "__wrapped__"):
        # Avoid double wrapping by checking __wrapped__
        wrap_function_wrapper(module, "run_in_executor", wrap_run_in_executor)
