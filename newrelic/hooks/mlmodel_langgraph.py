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

from newrelic.api.time_trace import current_trace
from newrelic.api.transaction import current_transaction
from newrelic.common.async_wrapper import coroutine_wrapper
from newrelic.common.object_wrapper import wrap_function_wrapper
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


def wrap_BackgroundExecutor_submit(wrapped, instance, args, kwargs):
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    try:
        func, args, kwargs = bind_submit(*args, **kwargs)
    except Exception:
        return wrapped(*args, **kwargs)

    func = context_wrapper(func, trace=trace, strict=True)
    return wrapped(func, *args, **kwargs)


def wrap_AsyncBackgroundExecutor_submit(wrapped, instance, args, kwargs):
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    try:
        func, args, kwargs = bind_submit(*args, **kwargs)
    except Exception:
        return wrapped(*args, **kwargs)

    context = ContextOf(trace=trace, strict=True)
    func = coroutine_wrapper(func, context)
    return wrapped(func, *args, **kwargs)


def instrument_langgraph_prebuilt_tool_node(module):
    if hasattr(module, "ToolNode"):
        if hasattr(module.ToolNode, "_execute_tool_sync"):
            wrap_function_wrapper(module, "ToolNode._execute_tool_sync", wrap_ToolNode__execute_tool_sync)
        if hasattr(module.ToolNode, "_execute_tool_async"):
            wrap_function_wrapper(module, "ToolNode._execute_tool_async", wrap_ToolNode__execute_tool_async)


def instrument_langgraph_pregel_executor(module):
    if hasattr(module, "BackgroundExecutor"):
        wrap_function_wrapper(module, "BackgroundExecutor.submit", wrap_BackgroundExecutor_submit)
    if hasattr(module, "AsyncBackgroundExecutor"):
        wrap_function_wrapper(module, "AsyncBackgroundExecutor.submit", wrap_AsyncBackgroundExecutor_submit)


def instrument_langgraph_internal_runnable(module):
    # langgraph._internal._runnable imports run_in_executor via `from ... import`,
    # binding the reference at import time. If that import happened before newrelic
    # hooks registered, langgraph's local reference is the unwrapped original.
    #
    # The real fix for this issue is to get users to initialize the agent correctly
    # before any imports, or to use the newrelic-admin wrapper. As a last ditch effort,
    # wrap the reference on this module the wrapped version is picked up at
    # compile time on StateGraph. This will only work if newrelic is initialized before
    # the StateGraph is compiled, but it should provide slightly better compatibility.
    if hasattr(module, "run_in_executor") and not hasattr(module.run_in_executor, "__wrapped__"):
        # Avoid double wrapping by checking __wrapped__
        wrap_function_wrapper(module, "run_in_executor", wrap_run_in_executor)
