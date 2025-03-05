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

import asyncio
import copy
import uuid

import langchain
import pydantic_core
import pytest
from langchain.tools import tool
from mock import patch
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.ml_testing_utils import (
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
    events_with_context_attrs,
    set_trace_info,
)
from testing_support.validators.validate_custom_event import validate_custom_event_count
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import validate_error_trace_attributes
from testing_support.validators.validate_transaction_error_event_count import validate_transaction_error_event_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.common.object_names import callable_name


@pytest.fixture
def single_arg_tool():
    @tool
    def _single_arg_tool(query: str):
        """A test tool that returns query string"""
        return query

    return _single_arg_tool


@pytest.fixture
def multi_arg_tool():
    @tool
    def _multi_arg_tool(first_num: int, second_num: int):
        """A test tool that adds two integers together"""
        return first_num + second_num

    return _multi_arg_tool


def events_sans_content(event):
    new_event = copy.deepcopy(event)
    for _event in new_event:
        del _event[1]["input"]
        if "output" in _event[1]:
            del _event[1]["output"]
    return new_event


single_arg_tool_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": None,
            "output": "Python Agent",
            "name": "_single_arg_tool",
            "description": "A test tool that returns query string",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'query': 'Python Agent'}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
        },
    )
]


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(single_arg_tool_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_single_arg_tool",
    scoped_metrics=[("Llm/tool/LangChain/run", 1)],
    rollup_metrics=[("Llm/tool/LangChain/run", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_langchain_single_arg_tool(set_trace_info, single_arg_tool):
    set_trace_info()
    with WithLlmCustomAttributes({"context": "attr"}):
        single_arg_tool.run({"query": "Python Agent"})


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(single_arg_tool_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_single_arg_tool_no_content",
    scoped_metrics=[("Llm/tool/LangChain/run", 1)],
    rollup_metrics=[("Llm/tool/LangChain/run", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_langchain_single_arg_tool_no_content(set_trace_info, single_arg_tool):
    set_trace_info()
    single_arg_tool.run({"query": "Python Agent"})


@reset_core_stats_engine()
@validate_custom_events(events_with_context_attrs(single_arg_tool_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_single_arg_tool_async",
    scoped_metrics=[("Llm/tool/LangChain/arun", 1)],
    rollup_metrics=[("Llm/tool/LangChain/arun", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_langchain_single_arg_tool_async(set_trace_info, single_arg_tool, loop):
    set_trace_info()
    with WithLlmCustomAttributes({"context": "attr"}):
        loop.run_until_complete(single_arg_tool.arun({"query": "Python Agent"}))


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(single_arg_tool_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_single_arg_tool_async_no_content",
    scoped_metrics=[("Llm/tool/LangChain/arun", 1)],
    rollup_metrics=[("Llm/tool/LangChain/arun", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_langchain_single_arg_tool_async_no_content(set_trace_info, single_arg_tool, loop):
    set_trace_info()
    loop.run_until_complete(single_arg_tool.arun({"query": "Python Agent"}))


multi_arg_tool_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": None,
            "output": "81",
            "name": "_multi_arg_tool",
            "description": "A test tool that adds two integers together",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'first_num': 53, 'second_num': 28}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
            "tags": "['python', 'test_tags']",
            "metadata.test": "langchain",
            "metadata.test_run": True,
        },
    )
]


@reset_core_stats_engine()
@validate_custom_events(multi_arg_tool_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_multi_arg_tool",
    scoped_metrics=[("Llm/tool/LangChain/run", 1)],
    rollup_metrics=[("Llm/tool/LangChain/run", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@background_task()
def test_langchain_multi_arg_tool(set_trace_info, multi_arg_tool):
    set_trace_info()
    multi_arg_tool.metadata = {"test_run": True}
    multi_arg_tool.tags = ["test_tags"]
    multi_arg_tool.run({"first_num": 53, "second_num": 28}, tags=["python"], metadata={"test": "langchain"})


@reset_core_stats_engine()
@validate_custom_events(multi_arg_tool_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_multi_arg_tool_async",
    scoped_metrics=[("Llm/tool/LangChain/arun", 1)],
    rollup_metrics=[("Llm/tool/LangChain/arun", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@background_task()
def test_langchain_multi_arg_tool_async(set_trace_info, multi_arg_tool, loop):
    set_trace_info()
    multi_arg_tool.metadata = {"test_run": True}
    multi_arg_tool.tags = ["test_tags"]
    loop.run_until_complete(
        multi_arg_tool.arun({"first_num": 53, "second_num": 28}, tags=["python"], metadata={"test": "langchain"})
    )


multi_arg_error_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "run_id": None,  # No run ID created on error
            "name": "_multi_arg_tool",
            "description": "A test tool that adds two integers together",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'first_num': 53}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
            "tags": "['test_tags', 'python']",
            "metadata.test": "langchain",
            "metadata.test_run": True,
            "error": True,
        },
    )
]


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(pydantic_core._pydantic_core.ValidationError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_custom_events(events_with_context_attrs(multi_arg_error_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_error_in_run",
    scoped_metrics=[("Llm/tool/LangChain/run", 1)],
    rollup_metrics=[("Llm/tool/LangChain/run", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@background_task()
def test_langchain_error_in_run(set_trace_info, multi_arg_tool):
    with pytest.raises(pydantic_core._pydantic_core.ValidationError):
        set_trace_info()
        # Only one argument is provided while the tool expects two to create an error
        with WithLlmCustomAttributes({"context": "attr"}):
            multi_arg_tool.run(
                {"first_num": 53}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
            )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(pydantic_core._pydantic_core.ValidationError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_custom_events(events_sans_content(multi_arg_error_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_error_in_run_no_content",
    scoped_metrics=[("Llm/tool/LangChain/run", 1)],
    rollup_metrics=[("Llm/tool/LangChain/run", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@background_task()
def test_langchain_error_in_run_no_content(set_trace_info, multi_arg_tool):
    with pytest.raises(pydantic_core._pydantic_core.ValidationError):
        set_trace_info()
        # Only one argument is provided while the tool expects two to create an error
        multi_arg_tool.run(
            {"first_num": 53}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
        )


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(pydantic_core._pydantic_core.ValidationError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_custom_events(events_with_context_attrs(multi_arg_error_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_error_in_run_async",
    scoped_metrics=[("Llm/tool/LangChain/arun", 1)],
    rollup_metrics=[("Llm/tool/LangChain/arun", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@background_task()
def test_langchain_error_in_run_async(set_trace_info, multi_arg_tool, loop):
    with pytest.raises(pydantic_core._pydantic_core.ValidationError):
        with WithLlmCustomAttributes({"context": "attr"}):
            set_trace_info()
            # Only one argument is provided while the tool expects two to create an error
            loop.run_until_complete(
                multi_arg_tool.arun(
                    {"first_num": 53}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
                )
            )


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(pydantic_core._pydantic_core.ValidationError), exact_attrs={"agent": {}, "intrinsic": {}, "user": {}}
)
@validate_custom_events(events_sans_content(multi_arg_error_recorded_events))
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_error_in_run_async_no_content",
    scoped_metrics=[("Llm/tool/LangChain/arun", 1)],
    rollup_metrics=[("Llm/tool/LangChain/arun", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@background_task()
def test_langchain_error_in_run_async_no_content(set_trace_info, multi_arg_tool, loop):
    with pytest.raises(pydantic_core._pydantic_core.ValidationError):
        set_trace_info()
        # Only one argument is provided while the tool expects two to create an error
        loop.run_until_complete(
            multi_arg_tool.arun(
                {"first_num": 53}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
            )
        )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_langchain_tool_outside_txn(single_arg_tool):
    single_arg_tool.run(
        {"query": "Python Agent"}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
    )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_langchain_tool_outside_txn_async(single_arg_tool, loop):
    loop.run_until_complete(
        single_arg_tool.arun(
            {"query": "Python Agent"}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
        )
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_langchain_tool_disabled_ai_monitoring_events_sync(set_trace_info, single_arg_tool):
    set_trace_info()
    single_arg_tool.run(
        {"query": "Python Agent"}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
    )


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_langchain_tool_disabled_ai_monitoring_events_async(set_trace_info, single_arg_tool, loop):
    set_trace_info()
    loop.run_until_complete(
        single_arg_tool.arun(
            {"query": "Python Agent"}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
        )
    )


def test_langchain_multiple_async_calls(set_trace_info, single_arg_tool, multi_arg_tool, loop):
    call1 = single_arg_tool_recorded_events.copy()
    call1[0][1]["run_id"] = "b1883d9d-10d6-4b67-a911-f72849704e92"
    call2 = multi_arg_tool_recorded_events.copy()
    call2[0][1]["run_id"] = "a58aa0c0-c854-4657-9e7b-4cce442f3b61"
    expected_events = call1 + call2

    @reset_core_stats_engine()
    @validate_custom_events(expected_events)
    @validate_custom_event_count(count=2)
    @validate_transaction_metrics(
        name="test_tool:test_langchain_multiple_async_calls.<locals>._test",
        custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
        background_task=True,
    )
    @background_task()
    def _test():
        set_trace_info()

        with patch("langchain_core.callbacks.manager.uuid", autospec=True) as mock_uuid:
            mock_uuid.uuid4.side_effect = [
                uuid.UUID("b1883d9d-10d6-4b67-a911-f72849704e92"),  # first call
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b61"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b61"),  # second call
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b63"),
                uuid.UUID("b1883d9d-10d6-4b67-a911-f72849704e93"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b64"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b65"),
                uuid.UUID("a58aa0c0-c854-4657-9e7b-4cce442f3b66"),
            ]

            loop.run_until_complete(
                asyncio.gather(
                    single_arg_tool.arun({"query": "Python Agent"}),
                    multi_arg_tool.arun(
                        {"first_num": 53, "second_num": 28},
                        tags=["python", "test_tags"],
                        metadata={"test": "langchain", "test_run": True},
                    ),
                )
            )

    _test()
