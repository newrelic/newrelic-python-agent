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
import pytest
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate
from langchain.tools import tool
from langchain_core.prompts import MessagesPlaceholder
from testing_support.fixtures import reset_core_stats_engine, validate_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@pytest.fixture
def tools():
    @tool
    def multi_arg_tool(first_num, second_num):
        """A test tool that adds two integers together"""
        return first_num + second_num

    return [multi_arg_tool]


@pytest.fixture
def prompt():
    return ChatPromptTemplate.from_messages(
        [
            ("system", "You are a world class algorithm for extracting information in structured formats."),
            ("human", "Use the given format to extract information from the following input: {input}"),
            ("human", "Tip: Make sure to answer in the correct format"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )


@reset_core_stats_engine()
@validate_transaction_metrics(
    name="test_agent:test_sync_agent",
    scoped_metrics=[("Llm/agent/LangChain/invoke", 1)],
    rollup_metrics=[("Llm/agent/LangChain/invoke", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_sync_agent(chat_openai_client, tools, prompt):
    agent = create_openai_functions_agent(chat_openai_client, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    response = agent_executor.invoke({"input": "Hello, world"})
    assert response


@reset_core_stats_engine()
@validate_transaction_metrics(
    name="test_agent:test_async_agent",
    scoped_metrics=[("Llm/agent/LangChain/ainvoke", 1)],
    rollup_metrics=[("Llm/agent/LangChain/ainvoke", 1)],
    custom_metrics=[(f"Supportability/Python/ML/LangChain/{langchain.__version__}", 1)],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_async_agent(loop, chat_openai_client, tools, prompt):
    agent = create_openai_functions_agent(chat_openai_client, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    loop.run_until_complete(agent_executor.ainvoke({"input": "Hello, world"}))
