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

import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings

LANGCHAIN_VERSION = get_package_version("langchain")

VECTORSTORE_CLASSES = {
    "langchain_community.vectorstores.alibabacloud_opensearch": "AlibabaCloudOpenSearch",
    "langchain_community.vectorstores.analyticdb": "AnalyticDB",
    "langchain_community.vectorstores.annoy": "Annoy",
    "langchain_community.vectorstores.astradb": "AstraDB",
    "langchain_community.vectorstores.atlas": "AtlasDB",
    "langchain_community.vectorstores.awadb": "AwaDB",
    "langchain_community.vectorstores.azure_cosmos_db": "AzureCosmosDBVectorSearch",
    "langchain_community.vectorstores.azuresearch": "AzureSearch",
    "langchain_community.vectorstores.bageldb": "Bagel",
    "langchain_community.vectorstores.baiducloud_vector_search": "BESVectorStore",
    "langchain_community.vectorstores.cassandra": "Cassandra",
    "langchain_community.vectorstores.chroma": "Chroma",
    "langchain_community.vectorstores.clarifai": "Clarifai",
    "langchain_community.vectorstores.clickhouse": "Clickhouse",
    "langchain_community.vectorstores.dashvector": "DashVector",
    "langchain_community.vectorstores.databricks_vector_search": "DatabricksVectorSearch",
    "langchain_community.vectorstores.deeplake": "DeepLake",
    "langchain_community.vectorstores.dingo": "Dingo",
    "langchain_community.vectorstores.elastic_vector_search": "ElasticVectorSearch",
    # "langchain_community.vectorstores.elastic_vector_search": "ElasticKnnSearch", # Deprecated
    "langchain_community.vectorstores.elasticsearch": "ElasticsearchStore",
    "langchain_community.vectorstores.epsilla": "Epsilla",
    "langchain_community.vectorstores.faiss": "FAISS",
    "langchain_community.vectorstores.hippo": "Hippo",
    "langchain_community.vectorstores.hologres": "Hologres",
    "langchain_community.vectorstores.lancedb": "LanceDB",
    "langchain_community.vectorstores.llm_rails": "LLMRails",
    "langchain_community.vectorstores.marqo": "Marqo",
    "langchain_community.vectorstores.matching_engine": "MatchingEngine",
    "langchain_community.vectorstores.meilisearch": "Meilisearch",
    "langchain_community.vectorstores.milvus": "Milvus",
    "langchain_community.vectorstores.momento_vector_index": "MomentoVectorIndex",
    "langchain_community.vectorstores.mongodb_atlas": "MongoDBAtlasVectorSearch",
    "langchain_community.vectorstores.myscale": "MyScale",
    "langchain_community.vectorstores.neo4j_vector": "Neo4jVector",
    "langchain_community.vectorstores.nucliadb": "NucliaDB",
    "langchain_community.vectorstores.opensearch_vector_search": "OpenSearchVectorSearch",
    "langchain_community.vectorstores.pgembedding": "PGEmbedding",
    "langchain_community.vectorstores.pgvecto_rs": "PGVecto_rs",
    "langchain_community.vectorstores.pgvector": "PGVector",
    "langchain_community.vectorstores.pinecone": "Pinecone",
    "langchain_community.vectorstores.qdrant": "Qdrant",
    "langchain_community.vectorstores.redis.base": "Redis",
    "langchain_community.vectorstores.rocksetdb": "Rockset",
    "langchain_community.vectorstores.scann": "ScaNN",
    "langchain_community.vectorstores.semadb": "SemaDB",
    "langchain_community.vectorstores.singlestoredb": "SingleStoreDB",
    "langchain_community.vectorstores.sklearn": "SKLearnVectorStore",
    "langchain_community.vectorstores.sqlitevss": "SQLiteVSS",
    "langchain_community.vectorstores.starrocks": "StarRocks",
    "langchain_community.vectorstores.supabase": "SupabaseVectorStore",
    "langchain_community.vectorstores.surrealdb": "SurrealDBStore",
    "langchain_community.vectorstores.tair": "Tair",
    "langchain_community.vectorstores.tencentvectordb": "TencentVectorDB",
    "langchain_community.vectorstores.tigris": "Tigris",
    "langchain_community.vectorstores.tiledb": "TileDB",
    "langchain_community.vectorstores.timescalevector": "TimescaleVector",
    "langchain_community.vectorstores.typesense": "Typesense",
    "langchain_community.vectorstores.usearch": "USearch",
    "langchain_community.vectorstores.vald": "Vald",
    "langchain_community.vectorstores.vearch": "Vearch",
    "langchain_community.vectorstores.vectara": "Vectara",
    "langchain_community.vectorstores.vespa": "VespaStore",
    "langchain_community.vectorstores.weaviate": "Weaviate",
    "langchain_community.vectorstores.xata": "XataVectorStore",
    "langchain_community.vectorstores.yellowbrick": "Yellowbrick",
    "langchain_community.vectorstores.zep": "ZepVectorStore",
    "langchain_community.vectorstores.docarray.hnsw": "DocArrayHnswSearch",
    "langchain_community.vectorstores.docarray.in_memory": "DocArrayInMemorySearch",
}


def bind_asimilarity_search(query, k, *args, **kwargs):
    return query, k


async def wrap_asimilarity_search(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    transaction.add_ml_model_info("Langchain", LANGCHAIN_VERSION)

    request_query, request_k = bind_asimilarity_search(*args, **kwargs)
    function_name = callable_name(wrapped)
    with FunctionTrace(name=function_name, group="Llm/vectorstore/Langchain") as ft:
        try:
            response = await wrapped(*args, **kwargs)
            available_metadata = get_trace_linking_metadata()
        except Exception as err:
            # Error logic goes here
            pass

    if not response:
        return response  # Should always be None

    # LLMVectorSearch
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")
    transaction_id = transaction.guid
    id = str(uuid.uuid4())
    request_query, request_k = bind_similarity_search(*args, **kwargs)
    duration = ft.duration
    response_number_of_documents = len(response)

    # Only in LlmVectorSearch dict
    LLMVectorSearch_dict = {
        "request.query": request_query,
        "request.k": request_k,
        "duration": duration,
        "response.number_of_documents": response_number_of_documents,
    }

    # In both LlmVectorSearch and LlmVectorSearchResult dicts
    LLMVectorSearch_union_dict = {
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction_id,
        "id": id,
        "vendor": "langchain",
        "ingest_source": "Python",
        "appName": transaction._application._name,
    }

    LLMVectorSearch_dict.update(LLMVectorSearch_union_dict)
    transaction.record_custom_event("LlmVectorSearch", LLMVectorSearch_dict)

    # LLMVectorSearchResult
    for index, doc in enumerate(response):
        search_id = str(uuid.uuid4())
        sequence = index
        page_content = getattr(doc, "page_content", "")
        metadata = getattr(doc, "metadata", "")

        metadata_dict = {"metadata.%s" % key: value for key, value in metadata.items()}

        LLMVectorSearchResult_dict = {
            "search_id": search_id,
            "sequence": sequence,
            "page_content": page_content,
        }

        LLMVectorSearchResult_dict.update(LLMVectorSearch_union_dict)
        LLMVectorSearchResult_dict.update(metadata_dict)

        transaction.record_custom_event("LlmVectorSearchResult", LLMVectorSearchResult_dict)

    return response


def bind_similarity_search(query, k, *args, **kwargs):
    return query, k


def wrap_similarity_search(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("Langchain", LANGCHAIN_VERSION)
    request_query, request_k = bind_similarity_search(*args, **kwargs)
    function_name = callable_name(wrapped)
    with FunctionTrace(name=function_name, group="Llm/vectorstore/Langchain") as ft:
        try:
            response = wrapped(*args, **kwargs)
            available_metadata = get_trace_linking_metadata()
        except Exception as exc:
            # Error logic goes here
            pass

    if not response:
        return response

    # LLMVectorSearch
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")
    transaction_id = transaction.guid
    id = str(uuid.uuid4())
    request_query, request_k = bind_similarity_search(*args, **kwargs)
    duration = ft.duration
    response_number_of_documents = len(response)

    # Only in LlmVectorSearch dict
    LLMVectorSearch_dict = {
        "request.query": request_query,
        "request.k": request_k,
        "duration": duration,
        "response.number_of_documents": response_number_of_documents,
    }

    # In both LlmVectorSearch and LlmVectorSearchResult dicts
    LLMVectorSearch_union_dict = {
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction_id,
        "id": id,
        "vendor": "langchain",
        "ingest_source": "Python",
        "appName": transaction._application._name,
    }

    LLMVectorSearch_dict.update(LLMVectorSearch_union_dict)
    transaction.record_custom_event("LlmVectorSearch", LLMVectorSearch_dict)

    # LLMVectorSearchResult
    for index, doc in enumerate(response):
        search_id = str(uuid.uuid4())
        sequence = index
        page_content = getattr(doc, "page_content", "")
        metadata = getattr(doc, "metadata", "")

        metadata_dict = {"metadata.%s" % key: value for key, value in metadata.items()}

        LLMVectorSearchResult_dict = {
            "search_id": search_id,
            "sequence": sequence,
            "page_content": page_content,
        }

        LLMVectorSearchResult_dict.update(LLMVectorSearch_union_dict)
        LLMVectorSearchResult_dict.update(metadata_dict)
        # This works in Python 3.9.8+
        # https://peps.python.org/pep-0584/
        # LLMVectorSearchResult_dict |= LLMVectorSearch_dict
        # LLMVectorSearchResult_dict |= metadata_dict

        transaction.record_custom_event("LlmVectorSearchResult", LLMVectorSearchResult_dict)

    return response


def wrap_tool_sync_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("Langchain", LANGCHAIN_VERSION)

    run_args = bind_args(wrapped, args, kwargs)

    metadata = {}
    metadata.update(run_args.get("metadata") or {})
    metadata.update(getattr(instance, "metadata", None) or {})

    tags = []
    tags.extend(run_args.get("tags") or [])
    tags.extend(getattr(instance, "tags", None) or [])

    tool_input = run_args.get("tool_input", "")
    tool_name = instance.name or ""
    tool_description = instance.description or ""

    span_id = None
    trace_id = None

    settings = transaction.settings if transaction.settings is not None else global_settings()
    app_name = settings.app_name
    tool_id = str(uuid.uuid4())

    function_name = wrapped.__name__

    with FunctionTrace(name=function_name, group="Llm/tool/Langchain") as ft:
        # Get trace information
        available_metadata = get_trace_linking_metadata()
        span_id = available_metadata.get("span.id", "")
        trace_id = available_metadata.get("trace.id", "")

        try:
            return_val = wrapped(**run_args)
        except Exception as exc:
            ft.notice_error(
                attributes={
                    "tool_id": tool_id,
                }
            )

            run_id = getattr(transaction, "_nr_run_manager_tools_info", {}).get("run_id", "")
            if hasattr(transaction, "_nr_run_manager_tools_info"):
                del transaction._nr_run_manager_tools_info

            # Make sure the builtin attributes take precedence over metadata attributes.
            error_tool_event_dict = {"metadata.%s" % key: value for key, value in metadata.items()}
            error_tool_event_dict.update(
                {
                    "id": tool_id,
                    "run_id": run_id,
                    "appName": app_name,
                    "name": tool_name,
                    "description": tool_description,
                    "span_id": span_id,
                    "trace_id": trace_id,
                    "transaction_id": transaction.guid,
                    "input": tool_input,
                    "vendor": "langchain",
                    "ingest_source": "Python",
                    "duration": ft.duration,
                    "tags": tags or "",
                    "error": True,
                }
            )

            transaction.record_custom_event("LlmTool", error_tool_event_dict)

            raise

    if not return_val:
        return return_val

    response = return_val

    run_id = getattr(transaction, "_nr_run_manager_tools_info", {}).get("run_id", "")
    if hasattr(transaction, "_nr_run_manager_tools_info"):
        del transaction._nr_run_manager_tools_info

    full_tool_event_dict = {"metadata.%s" % key: value for key, value in metadata.items()}
    full_tool_event_dict.update(
        {
            "id": tool_id,
            "run_id": run_id,
            "appName": app_name,
            "output": str(response),
            "name": tool_name,
            "description": tool_description,
            "span_id": span_id,
            "trace_id": trace_id,
            "transaction_id": transaction.guid,
            "input": tool_input,
            "vendor": "langchain",
            "ingest_source": "Python",
            "duration": ft.duration,
            "tags": tags or "",
        }
    )

    transaction.record_custom_event("LlmTool", full_tool_event_dict)

    return return_val


def wrap_on_tool_start(wrapped, instance, args, kwargs):
    run_manager = wrapped(*args, **kwargs)
    transaction = current_transaction()
    if not transaction:
        return run_manager
    # Only capture the first run_id.
    if not hasattr(transaction, "_nr_run_manager_tools_info"):
        transaction._nr_run_manager_tools_info = {
            "run_id": run_manager.run_id,
        }

    return run_manager


def instrument_langchain_vectorstore_similarity_search(module):
    vector_class = VECTORSTORE_CLASSES.get(module.__name__)

    if vector_class and hasattr(getattr(module, vector_class, ""), "similarity_search"):
        wrap_function_wrapper(module, "%s.similarity_search" % vector_class, wrap_similarity_search)
    if vector_class and hasattr(getattr(module, vector_class, ""), "asimilarity_search"):
        wrap_function_wrapper(module, "%s.asimilarity_search" % vector_class, wrap_asimilarity_search)


def instrument_langchain_core_tools(module):
    if hasattr(getattr(module, "BaseTool"), "run"):
        wrap_function_wrapper(module, "BaseTool.run", wrap_tool_sync_run)


def instrument_langchain_callbacks_manager(module):
    if hasattr(getattr(module, "CallbackManager"), "on_tool_start"):
        wrap_function_wrapper(module, "CallbackManager.on_tool_start", wrap_on_tool_start)
