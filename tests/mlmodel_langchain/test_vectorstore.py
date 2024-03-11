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

import copy
import os

import langchain
import pytest
from conftest import (  # pylint: disable=E0611
    disabled_ai_monitoring_record_content_settings,
    disabled_ai_monitoring_settings,
)
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores.faiss import FAISS
from testing_support.fixtures import (
    reset_core_stats_engine,
    validate_attributes,
    validate_custom_event_count,
)
from testing_support.validators.validate_custom_events import validate_custom_events
from testing_support.validators.validate_error_trace_attributes import (
    validate_error_trace_attributes,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute
from newrelic.common.object_names import callable_name


def events_sans_content(event):
    new_event = copy.deepcopy(event)
    for _event in new_event:
        if "request.query" in _event[1]:
            del _event[1]["request.query"]
        if "page_content" in _event[1]:
            del _event[1]["page_content"]
    return new_event


vectorstore_recorded_events = [
    (
        {"type": "LlmVectorSearch", "timestamp": 1702052394890},
        {
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "id": None,  # UUID that changes with each run
            "vendor": "langchain",
            "ingest_source": "Python",
            "appName": "Python Agent Test (mlmodel_langchain)",
            "request.query": "Complete this sentence: Hello",
            "request.k": 1,
            "duration": None,  # Changes with every run
            "response.number_of_documents": 1,
        },
    ),
    (
        {"type": "LlmVectorSearchResult", "timestamp": 1702052424031},
        {
            "search_id": None,  # UUID that changes with each run
            "sequence": 0,
            "page_content": "Hello world!\n1",
            "span_id": None,
            "trace_id": "trace-id",
            "transaction_id": "transaction-id",
            "llm.conversation_id": "my-awesome-id",
            "llm.foo": "bar",
            "id": None,  # UUID that changes with each run
            "vendor": "langchain",
            "ingest_source": "Python",
            "appName": "Python Agent Test (mlmodel_langchain)",
            "metadata.source": os.path.join(os.path.dirname(__file__), "hello.pdf"),
            "metadata.page": 0,
        },
    ),
]


_test_vectorstore_modules_instrumented_ignored_classes = set(
    [
        "VectorStore",  # Base class
        "ElasticKnnSearch",  # Deprecated, so we will not be instrumenting this.
    ]
)


# Test to check if all classes containing "similarity_search"
# method are instrumented.  Prints out anything that is not
# instrumented to identify when new vectorstores are added.
def test_vectorstore_modules_instrumented():
    from langchain_community import vectorstores

    vector_store_classes = tuple(vectorstores.__all__)
    uninstrumented_sync_classes = []
    uninstrumented_async_classes = []
    for class_name in vector_store_classes:
        class_ = getattr(vectorstores, class_name)
        if (
            not hasattr(class_, "similarity_search")
            or class_name in _test_vectorstore_modules_instrumented_ignored_classes
        ):
            # If "similarity_search" is found, "asimilarity_search" will
            # also be found, so separate logic is not necessary to check this.
            continue

        if not hasattr(getattr(class_, "similarity_search"), "__wrapped__"):
            uninstrumented_sync_classes.append(class_name)
        if not hasattr(getattr(class_, "asimilarity_search"), "__wrapped__"):
            uninstrumented_async_classes.append(class_name)

    assert not uninstrumented_sync_classes, "Uninstrumented sync classes found: %s" % str(uninstrumented_sync_classes)
    assert not uninstrumented_async_classes, "Uninstrumented async classes found: %s" % str(
        uninstrumented_async_classes
    )


@reset_core_stats_engine()
@validate_custom_events(vectorstore_recorded_events)
# Two OpenAI LlmEmbedded, two LangChain LlmVectorSearch
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_vectorstore:test_pdf_pagesplitter_vectorstore_in_txn",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_pdf_pagesplitter_vectorstore_in_txn(set_trace_info, embedding_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    script_dir = os.path.dirname(__file__)
    loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
    docs = loader.load()

    faiss_index = FAISS.from_documents(docs, embedding_openai_client)
    docs = faiss_index.similarity_search("Complete this sentence: Hello", k=1)
    assert "Hello world" in docs[0].page_content


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(vectorstore_recorded_events))
# Two OpenAI LlmEmbedded, two LangChain LlmVectorSearch
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_vectorstore:test_pdf_pagesplitter_vectorstore_in_txn_no_content",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_pdf_pagesplitter_vectorstore_in_txn_no_content(set_trace_info, embedding_openai_client):
    set_trace_info()
    add_custom_attribute("llm.conversation_id", "my-awesome-id")
    add_custom_attribute("llm.foo", "bar")
    add_custom_attribute("non_llm_attr", "python-agent")

    script_dir = os.path.dirname(__file__)
    loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
    docs = loader.load()

    faiss_index = FAISS.from_documents(docs, embedding_openai_client)
    docs = faiss_index.similarity_search("Complete this sentence: Hello", k=1)
    assert "Hello world" in docs[0].page_content


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_pdf_pagesplitter_vectorstore_outside_txn(set_trace_info, embedding_openai_client):
    set_trace_info()

    script_dir = os.path.dirname(__file__)
    loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
    docs = loader.load()

    faiss_index = FAISS.from_documents(docs, embedding_openai_client)
    docs = faiss_index.similarity_search("Complete this sentence: Hello", k=1)
    assert "Hello world" in docs[0].page_content


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
@background_task()
def test_pdf_pagesplitter_vectorstore_ai_monitoring_disabled(set_trace_info, embedding_openai_client):
    set_trace_info()

    script_dir = os.path.dirname(__file__)
    loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
    docs = loader.load()

    faiss_index = FAISS.from_documents(docs, embedding_openai_client)
    docs = faiss_index.similarity_search("Complete this sentence: Hello", k=1)
    assert "Hello world" in docs[0].page_content


@reset_core_stats_engine()
@validate_custom_events(vectorstore_recorded_events)
# Two OpenAI LlmEmbedded, two LangChain LlmVectorSearch
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_vectorstore:test_async_pdf_pagesplitter_vectorstore_in_txn",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_async_pdf_pagesplitter_vectorstore_in_txn(loop, set_trace_info, embedding_openai_client):
    async def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = await FAISS.afrom_documents(docs, embedding_openai_client)
        docs = await faiss_index.asimilarity_search("Complete this sentence: Hello", k=1)
        return docs

    docs = loop.run_until_complete(_test())
    assert "Hello world" in docs[0].page_content


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_custom_events(events_sans_content(vectorstore_recorded_events))
# Two OpenAI LlmEmbedded, two LangChain LlmVectorSearch
@validate_custom_event_count(count=4)
@validate_transaction_metrics(
    name="test_vectorstore:test_async_pdf_pagesplitter_vectorstore_in_txn_no_content",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@validate_attributes("agent", ["llm"])
@background_task()
def test_async_pdf_pagesplitter_vectorstore_in_txn_no_content(loop, set_trace_info, embedding_openai_client):
    async def _test():
        set_trace_info()
        add_custom_attribute("llm.conversation_id", "my-awesome-id")
        add_custom_attribute("llm.foo", "bar")
        add_custom_attribute("non_llm_attr", "python-agent")

        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = await FAISS.afrom_documents(docs, embedding_openai_client)
        docs = await faiss_index.asimilarity_search("Complete this sentence: Hello", k=1)
        return docs

    docs = loop.run_until_complete(_test())
    assert "Hello world" in docs[0].page_content


@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_async_pdf_pagesplitter_vectorstore_outside_txn(loop, set_trace_info, embedding_openai_client):
    async def _test():
        set_trace_info()

        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = await FAISS.afrom_documents(docs, embedding_openai_client)
        docs = await faiss_index.asimilarity_search("Complete this sentence: Hello", k=1)
        return docs

    docs = loop.run_until_complete(_test())
    assert "Hello world" in docs[0].page_content


@disabled_ai_monitoring_settings
@reset_core_stats_engine()
@validate_custom_event_count(count=0)
def test_async_pdf_pagesplitter_vectorstore_ai_monitoring_disabled(loop, set_trace_info, embedding_openai_client):
    async def _test():
        set_trace_info()

        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = await FAISS.afrom_documents(docs, embedding_openai_client)
        docs = await faiss_index.asimilarity_search("Complete this sentence: Hello", k=1)
        return docs

    docs = loop.run_until_complete(_test())
    assert "Hello world" in docs[0].page_content


vectorstore_error_events = [
    (
        {"type": "LlmVectorSearch"},
        {
            "id": None,  # UUID that varies with each run
            "appName": "Python Agent Test (mlmodel_langchain)",
            "transaction_id": "transaction-id",
            "span_id": None,
            "trace_id": "trace-id",
            "vendor": "Langchain",
            "ingest_source": "Python",
            "error": True,
        },
    ),
]


@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    required_params={"user": ["vector_store_id"], "intrinsic": [], "agent": []},
)
@validate_custom_events(vectorstore_error_events)
@validate_transaction_metrics(
    name="test_vectorstore:test_vectorstore_error_no_query",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_vectorstore_error_no_query(set_trace_info, embedding_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = FAISS.from_documents(docs, embedding_openai_client)
        faiss_index.similarity_search(k=1)


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(TypeError),
    required_params={"user": ["vector_store_id"], "intrinsic": [], "agent": []},
)
@validate_custom_events(events_sans_content(vectorstore_error_events))
@validate_transaction_metrics(
    name="test_vectorstore:test_vectorstore_error_no_query_no_content",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_vectorstore_error_no_query_no_content(set_trace_info, embedding_openai_client):
    with pytest.raises(TypeError):
        set_trace_info()
        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = FAISS.from_documents(docs, embedding_openai_client)
        faiss_index.similarity_search(k=1)


@reset_core_stats_engine()
@validate_error_trace_attributes(
    callable_name(TypeError),
    required_params={"user": ["vector_store_id"], "intrinsic": [], "agent": []},
)
@validate_custom_events(vectorstore_error_events)
@validate_transaction_metrics(
    name="test_vectorstore:test_async_vectorstore_error_no_query",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_vectorstore_error_no_query(loop, set_trace_info, embedding_openai_client):
    async def _test():
        set_trace_info()

        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = await FAISS.afrom_documents(docs, embedding_openai_client)
        docs = await faiss_index.asimilarity_search(k=1)
        return docs

    with pytest.raises(TypeError):
        loop.run_until_complete(_test())


@reset_core_stats_engine()
@disabled_ai_monitoring_record_content_settings
@validate_error_trace_attributes(
    callable_name(TypeError),
    required_params={"user": ["vector_store_id"], "intrinsic": [], "agent": []},
)
@validate_custom_events(events_sans_content(vectorstore_error_events))
@validate_transaction_metrics(
    name="test_vectorstore:test_async_vectorstore_error_no_query_no_content",
    custom_metrics=[
        ("Supportability/Python/ML/Langchain/%s" % langchain.__version__, 1),
    ],
    background_task=True,
)
@background_task()
def test_async_vectorstore_error_no_query_no_content(loop, set_trace_info, embedding_openai_client):
    async def _test():
        set_trace_info()

        script_dir = os.path.dirname(__file__)
        loader = PyPDFLoader(os.path.join(script_dir, "hello.pdf"))
        docs = loader.load()

        faiss_index = await FAISS.afrom_documents(docs, embedding_openai_client)
        docs = await faiss_index.asimilarity_search(k=1)
        return docs

    with pytest.raises(TypeError):
        loop.run_until_complete(_test())
