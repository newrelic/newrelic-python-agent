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

import langchain
import pydantic
import pytest
from langchain.tools import tool
from testing_support.fixtures import (  # override_application_settings,
    override_application_settings,
    reset_core_stats_engine,
    validate_custom_event_count,
    validate_transaction_error_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.common.object_names import callable_name

disabled_custom_insights_settings = {"custom_insights_events.enabled": False}


@tool
def single_arg_tool(query: str):
    """A test tool that returns query string"""
    return query


@tool
def multi_arg_tool(first_num: int, second_num: int):
    """A test tool that adds two integers together"""
    return first_num + second_num


single_arg_tool_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_langchain)",
            "run_id": None,
            "output": "Python Agent",
            "name": "single_arg_tool",
            "description": "single_arg_tool(query: str) - A test tool that returns query string",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'query': 'Python Agent'}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
            "tags": "",
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(single_arg_tool_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_single_arg_tool",
    scoped_metrics=[("Llm/tool/Langchain/run", 1)],
    rollup_metrics=[("Llm/tool/Langchain/run", 1)],
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_single_arg_tool(set_trace_info):
    set_trace_info()
    single_arg_tool.run({"query": "Python Agent"})


multi_arg_tool_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_langchain)",
            "run_id": None,
            "output": "81",
            "name": "multi_arg_tool",
            "description": "multi_arg_tool(first_num: int, second_num: int) - A test tool that adds two integers together",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "input": "{'first_num': 53, 'second_num': 28}",
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": None,
            "tags": "['test_tags', 'python']",
            "metadata.test": "langchain",
            "metadata.test_run": True,
        },
    ),
]


@reset_core_stats_engine()
@validate_custom_events(multi_arg_tool_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_multi_arg_tool",
    scoped_metrics=[("Llm/tool/Langchain/run", 1)],
    rollup_metrics=[("Llm/tool/Langchain/run", 1)],
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_multi_arg_tool(set_trace_info):
    set_trace_info()
    multi_arg_tool.run(
        {"first_num": 53, "second_num": 28},
        tags=["test_tags", "python"],
        metadata={"test_run": True, "test": "langchain"},
    )


@reset_core_stats_engine()
@validate_custom_events(multi_arg_tool_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_tags_and_metadata_on_instance",
    scoped_metrics=[("Llm/tool/Langchain/run", 1)],
    rollup_metrics=[("Llm/tool/Langchain/run", 1)],
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_tags_and_metadata_on_instance(set_trace_info):
    set_trace_info()
    multi_arg_tool.metadata = {"test_run": True, "test": "langchain"}
    multi_arg_tool.tags = ["test_tags", "python"]
    multi_arg_tool.run(
        {"first_num": 53, "second_num": 28},
    )


multi_arg_error_recorded_events = [
    (
        {"type": "LlmTool"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_langchain)",
            "run_id": "", # No run ID created on error
            "name": "multi_arg_tool",
            "description": "multi_arg_tool(first_num: int, second_num: int) - A test tool that adds two integers together",
            "transaction_id": "transaction-id",
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
    ),
]


@reset_core_stats_engine()
@validate_transaction_error_event_count(1)
@validate_error_trace_attributes(
    callable_name(pydantic.v1.error_wrappers.ValidationError),
    exact_attrs={
        "agent": {},
        "intrinsic": {},
        "user": {},
    },
)
@validate_custom_events(multi_arg_error_recorded_events)
@validate_custom_event_count(count=1)
@validate_transaction_metrics(
    name="test_tool:test_langchain_error_in_run",
    scoped_metrics=[("Llm/tool/Langchain/run", 1)],
    rollup_metrics=[("Llm/tool/Langchain/run", 1)],
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_error_in_run(set_trace_info):
    with pytest.raises(pydantic.v1.error_wrappers.ValidationError):
        set_trace_info()
        # Only one argument is provided while the tool expects two to create an error
        multi_arg_tool.run(
            {"first_num": 53}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
        )


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_langchain_tool_outside_txn():
    single_arg_tool.run(
        {"query": "Python Agent"}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
    )


@override_application_settings(disabled_custom_insights_settings)
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@validate_transaction_metrics(
    name="test_tool:test_langchain_tool_disabled_custom_insights_events",
    scoped_metrics=[("Llm/tool/Langchain/run", 1)],
    rollup_metrics=[("Llm/tool/Langchain/run", 1)],
    custom_metrics=[
        ("Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_langchain_tool_disabled_custom_insights_events(set_trace_info):
    set_trace_info()
    single_arg_tool.run(
        {"query": "Python Agent"}, tags=["test_tags", "python"], metadata={"test_run": True, "test": "langchain"}
    )
