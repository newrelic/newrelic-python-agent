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

import logging
import sys
import time
import traceback
import uuid

from newrelic.api.function_trace import FunctionTrace
from newrelic.api.time_trace import current_trace, get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.llm_utils import AsyncGeneratorProxy, GeneratorProxy
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper
from newrelic.common.package_version_utils import get_package_version
from newrelic.common.signature import bind_args
from newrelic.core.config import global_settings
from newrelic.core.context import ContextOf, context_wrapper

_logger = logging.getLogger(__name__)
LANGCHAIN_VERSION = get_package_version("langchain")
EXCEPTION_HANDLING_FAILURE_LOG_MESSAGE = "Exception occurred in langchain instrumentation: While reporting an exception in langchain, another exception occurred. Report this issue to New Relic Support.\n%s"
RECORD_EVENTS_FAILURE_LOG_MESSAGE = "Exception occurred in langchain instrumentation: Failed to record LLM events. Report this issue to New Relic Support.\n%s"
VECTORSTORE_CLASSES = {
    "langchain_community.vectorstores.aerospike": "Aerospike",
    "langchain_community.vectorstores.alibabacloud_opensearch": "AlibabaCloudOpenSearch",
    "langchain_community.vectorstores.analyticdb": "AnalyticDB",
    "langchain_community.vectorstores.annoy": "Annoy",
    "langchain_community.vectorstores.apache_doris": "ApacheDoris",
    "langchain_community.vectorstores.aperturedb": "ApertureDB",
    "langchain_community.vectorstores.astradb": "AstraDB",
    "langchain_community.vectorstores.atlas": "AtlasDB",
    "langchain_community.vectorstores.awadb": "AwaDB",
    "langchain_community.vectorstores.azure_cosmos_db_no_sql": "AzureCosmosDBNoSqlVectorSearch",
    "langchain_community.vectorstores.azure_cosmos_db": "AzureCosmosDBVectorSearch",
    "langchain_community.vectorstores.azuresearch": "AzureSearch",
    "langchain_community.vectorstores.baiduvectordb": "BaiduVectorDB",
    "langchain_community.vectorstores.bageldb": "Bagel",
    "langchain_community.vectorstores.baiducloud_vector_search": "BESVectorStore",
    "langchain_community.vectorstores.bigquery_vector_search": "BigQueryVectorSearch",
    "langchain_community.vectorstores.cassandra": "Cassandra",
    "langchain_community.vectorstores.chroma": "Chroma",
    "langchain_community.vectorstores.clarifai": "Clarifai",
    "langchain_community.vectorstores.clickhouse": "Clickhouse",
    "langchain_community.vectorstores.couchbase": "CouchbaseVectorStore",
    "langchain_community.vectorstores.dashvector": "DashVector",
    "langchain_community.vectorstores.databricks_vector_search": "DatabricksVectorSearch",
    "langchain_community.vectorstores.deeplake": "DeepLake",
    "langchain_community.vectorstores.dingo": "Dingo",
    "langchain_community.vectorstores.documentdb": "DocumentDBVectorSearch",
    "langchain_community.vectorstores.duckdb": "DuckDB",
    "langchain_community.vectorstores.ecloud_vector_search": "EcloudESVectorStore",
    "langchain_community.vectorstores.elastic_vector_search": ["ElasticVectorSearch", "ElasticKnnSearch"],
    "langchain_community.vectorstores.elasticsearch": "ElasticsearchStore",
    "langchain_community.vectorstores.epsilla": "Epsilla",
    "langchain_community.vectorstores.faiss": "FAISS",
    "langchain_community.vectorstores.hanavector": "HanaDB",
    "langchain_community.vectorstores.hippo": "Hippo",
    "langchain_community.vectorstores.hologres": "Hologres",
    "langchain_community.vectorstores.infinispanvs": "InfinispanVS",
    "langchain_community.vectorstores.inmemory": "InMemoryVectorStore",
    "langchain_community.vectorstores.kdbai": "KDBAI",
    "langchain_community.vectorstores.kinetica": "Kinetica",
    "langchain_community.vectorstores.lancedb": "LanceDB",
    "langchain_community.vectorstores.lantern": "Lantern",
    "langchain_community.vectorstores.llm_rails": "LLMRails",
    "langchain_community.vectorstores.manticore_search": "ManticoreSearch",
    "langchain_community.vectorstores.marqo": "Marqo",
    "langchain_community.vectorstores.matching_engine": "MatchingEngine",
    "langchain_community.vectorstores.meilisearch": "Meilisearch",
    "langchain_community.vectorstores.milvus": "Milvus",
    "langchain_community.vectorstores.momento_vector_index": "MomentoVectorIndex",
    "langchain_community.vectorstores.mongodb_atlas": "MongoDBAtlasVectorSearch",
    "langchain_community.vectorstores.myscale": "MyScale",
    "langchain_community.vectorstores.neo4j_vector": "Neo4jVector",
    "langchain_community.vectorstores.thirdai_neuraldb": ["NeuralDBClientVectorStore", "NeuralDBVectorStore"],
    "langchain_community.vectorstores.nucliadb": "NucliaDB",
    "langchain_community.vectorstores.oraclevs": "OracleVS",
    "langchain_community.vectorstores.opensearch_vector_search": "OpenSearchVectorSearch",
    "langchain_community.vectorstores.pathway": "PathwayVectorClient",
    "langchain_community.vectorstores.pgembedding": "PGEmbedding",
    "langchain_community.vectorstores.pgvecto_rs": "PGVecto_rs",
    "langchain_community.vectorstores.pgvector": "PGVector",
    "langchain_community.vectorstores.pinecone": "Pinecone",
    "langchain_community.vectorstores.qdrant": "Qdrant",
    "langchain_community.vectorstores.redis": "Redis",
    "langchain_community.vectorstores.relyt": "Relyt",
    "langchain_community.vectorstores.rocksetdb": "Rockset",
    "langchain_community.vectorstores.scann": "ScaNN",
    "langchain_community.vectorstores.semadb": "SemaDB",
    "langchain_community.vectorstores.singlestoredb": "SingleStoreDB",
    "langchain_community.vectorstores.sklearn": "SKLearnVectorStore",
    "langchain_community.vectorstores.sqlitevec": "SQLiteVec",
    "langchain_community.vectorstores.sqlitevss": "SQLiteVSS",
    "langchain_community.vectorstores.starrocks": "StarRocks",
    "langchain_community.vectorstores.supabase": "SupabaseVectorStore",
    "langchain_community.vectorstores.surrealdb": "SurrealDBStore",
    "langchain_community.vectorstores.tablestore": "TablestoreVectorStore",
    "langchain_community.vectorstores.tair": "Tair",
    "langchain_community.vectorstores.tencentvectordb": "TencentVectorDB",
    "langchain_community.vectorstores.tidb_vector": "TiDBVectorStore",
    "langchain_community.vectorstores.tigris": "Tigris",
    "langchain_community.vectorstores.tiledb": "TileDB",
    "langchain_community.vectorstores.timescalevector": "TimescaleVector",
    "langchain_community.vectorstores.typesense": "Typesense",
    "langchain_community.vectorstores.upstash": "UpstashVectorStore",
    "langchain_community.vectorstores.usearch": "USearch",
    "langchain_community.vectorstores.vald": "Vald",
    "langchain_community.vectorstores.vdms": "VDMS",
    "langchain_community.vectorstores.vearch": "Vearch",
    "langchain_community.vectorstores.vectara": "Vectara",
    "langchain_community.vectorstores.vespa": "VespaStore",
    "langchain_community.vectorstores.vlite": "VLite",
    "langchain_community.vectorstores.weaviate": "Weaviate",
    "langchain_community.vectorstores.xata": "XataVectorStore",
    "langchain_community.vectorstores.yellowbrick": "Yellowbrick",
    "langchain_community.vectorstores.zep_cloud": "ZepCloudVectorStore",
    "langchain_community.vectorstores.zep": "ZepVectorStore",
    "langchain_community.vectorstores.docarray": ["DocArrayHnswSearch", "DocArrayInMemorySearch"],
}


def _construct_base_agent_event_dict(agent_name, agent_id, transaction):
    try:
        linking_metadata = get_trace_linking_metadata()

        agent_event_dict = {
            "id": agent_id,
            "name": agent_name,
            "span_id": linking_metadata.get("span.id"),
            "trace_id": linking_metadata.get("trace.id"),
            "vendor": "langchain",
            "ingest_source": "Python",
        }
        agent_event_dict.update(_get_llm_metadata(transaction))
    except Exception:
        agent_event_dict = {}
        _logger.warning(RECORD_EVENTS_FAILURE_LOG_MESSAGE, exc_info=True)

    return agent_event_dict


class AgentObjectProxy(ObjectProxy):
    def invoke(self, *args, **kwargs):
        transaction = current_transaction()

        agent_name = getattr(self.__wrapped__, "name", None)
        agent_id = str(uuid.uuid4())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        function_trace_name = f"invoke/{agent_name}"

        ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangChain")
        ft.__enter__()
        try:
            return_val = self.__wrapped__.invoke(*args, **kwargs)
        except Exception:
            ft.notice_error(attributes={"agent_id": agent_id})
            ft.__exit__(*sys.exc_info())
            # If we hit an exception, append the error attribute and duration from the exited function trace
            agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
            transaction.record_custom_event("LlmAgent", agent_event_dict)
            raise

        ft.__exit__(None, None, None)
        agent_event_dict.update({"duration": ft.duration * 1000})

        transaction.record_custom_event("LlmAgent", agent_event_dict)

        return return_val

    async def ainvoke(self, *args, **kwargs):
        transaction = current_transaction()

        agent_name = getattr(self.__wrapped__, "name", None)
        agent_id = str(uuid.uuid4())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        function_trace_name = f"ainvoke/{agent_name}"

        ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangChain")
        ft.__enter__()
        try:
            return_val = await self.__wrapped__.ainvoke(*args, **kwargs)
        except Exception:
            ft.notice_error(attributes={"agent_id": agent_id})
            ft.__exit__(*sys.exc_info())
            # If we hit an exception, append the error attribute and duration from the exited function trace
            agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
            transaction.record_custom_event("LlmAgent", agent_event_dict)
            raise

        ft.__exit__(None, None, None)
        agent_event_dict.update({"duration": ft.duration * 1000})

        transaction.record_custom_event("LlmAgent", agent_event_dict)

        return return_val

    def stream(self, *args, **kwargs):
        transaction = current_transaction()

        agent_name = getattr(self.__wrapped__, "name", None)
        agent_id = str(uuid.uuid4())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        function_trace_name = f"stream/{agent_name}"

        ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangChain")
        ft.__enter__()
        try:
            return_val = self.__wrapped__.stream(*args, **kwargs)
            return_val = GeneratorProxy(
                return_val,
                on_stop_iteration=self._nr_on_stop_iteration(ft, agent_event_dict),
                on_error=self._nr_on_error(ft, agent_event_dict, agent_id),
            )
        except Exception:
            self._nr_on_error(ft, agent_event_dict, agent_id)(transaction)
            raise

        return return_val

    def astream(self, *args, **kwargs):
        transaction = current_transaction()

        agent_name = getattr(self.__wrapped__, "name", None)
        agent_id = str(uuid.uuid4())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        function_trace_name = f"astream/{agent_name}"

        ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangChain")
        ft.__enter__()
        try:
            return_val = self.__wrapped__.astream(*args, **kwargs)
            return_val = AsyncGeneratorProxy(
                return_val,
                on_stop_iteration=self._nr_on_stop_iteration(ft, agent_event_dict),
                on_error=self._nr_on_error(ft, agent_event_dict, agent_id),
            )
        except Exception:
            self._nr_on_error(ft, agent_event_dict, agent_id)(transaction)
            raise

        return return_val

    def transform(self, *args, **kwargs):
        transaction = current_transaction()

        agent_name = getattr(self.__wrapped__, "name", None)
        agent_id = str(uuid.uuid4())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        function_trace_name = f"stream/{agent_name}"

        ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangChain")
        ft.__enter__()
        try:
            return_val = self.__wrapped__.transform(*args, **kwargs)
            return_val = GeneratorProxy(
                return_val,
                on_stop_iteration=self._nr_on_stop_iteration(ft, agent_event_dict),
                on_error=self._nr_on_error(ft, agent_event_dict, agent_id),
            )
        except Exception:
            self._nr_on_error(ft, agent_event_dict, agent_id)(transaction)
            raise

        return return_val

    def atransform(self, *args, **kwargs):
        transaction = current_transaction()

        agent_name = getattr(self.__wrapped__, "name", None)
        agent_id = str(uuid.uuid4())
        agent_event_dict = _construct_base_agent_event_dict(agent_name, agent_id, transaction)
        function_trace_name = f"astream/{agent_name}"

        ft = FunctionTrace(name=function_trace_name, group="Llm/agent/LangChain")
        ft.__enter__()
        try:
            return_val = self.__wrapped__.atransform(*args, **kwargs)
            return_val = AsyncGeneratorProxy(
                return_val,
                on_stop_iteration=self._nr_on_stop_iteration(ft, agent_event_dict),
                on_error=self._nr_on_error(ft, agent_event_dict, agent_id),
            )
        except Exception:
            self._nr_on_error(ft, agent_event_dict, agent_id)(transaction)
            raise

        return return_val

    def _nr_on_stop_iteration(self, ft, agent_event_dict):
        def _on_stop_iteration(proxy, transaction):
            ft.__exit__(None, None, None)
            if agent_event_dict:
                agent_event_dict.update({"duration": ft.duration * 1000})
                transaction.record_custom_event("LlmAgent", agent_event_dict)
                agent_event_dict.clear()

        return _on_stop_iteration

    def _nr_on_error(self, ft, agent_event_dict, agent_id):
        def _on_error(proxy, transaction):
            ft.notice_error(attributes={"agent_id": agent_id})
            ft.__exit__(*sys.exc_info())
            if agent_event_dict:
                # If we hit an exception, append the error attribute and duration from the exited function trace
                agent_event_dict.update({"duration": ft.duration * 1000, "error": True})
                transaction.record_custom_event("LlmAgent", agent_event_dict)
                agent_event_dict.clear()

        return _on_error


def bind_submit(func, *args, **kwargs):
    return {"func": func, "args": args, "kwargs": kwargs}


def wrap_ContextThreadPoolExecutor_submit(wrapped, instance, args, kwargs):
    trace = current_trace()
    if not trace:
        return wrapped(*args, **kwargs)

    # Use hardened function signature bind so we have safety net catchall of args and kwargs.
    bound_args = bind_submit(*args, **kwargs)
    bound_args["func"] = context_wrapper(bound_args["func"], trace=trace, strict=True)
    return wrapped(bound_args["func"], *bound_args["args"], **bound_args["kwargs"])


def _create_error_vectorstore_events(transaction, search_id, args, kwargs, linking_metadata, wrapped):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    bound_args = bind_args(wrapped, args, kwargs)
    request_query = bound_args["query"]
    request_k = bound_args["k"]
    llm_metadata_dict = _get_llm_metadata(transaction)
    vectorstore_error_dict = {
        "request.k": request_k,
        "id": search_id,
        "span_id": span_id,
        "trace_id": trace_id,
        "vendor": "langchain",
        "ingest_source": "Python",
        "error": True,
    }

    if settings.ai_monitoring.record_content.enabled:
        vectorstore_error_dict["request.query"] = request_query

    vectorstore_error_dict.update(llm_metadata_dict)
    transaction.record_custom_event("LlmVectorSearch", vectorstore_error_dict)


async def wrap_asimilarity_search(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    search_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/vectorstore/LangChain")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        response = await wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"vector_store_id": search_id})
        ft.__exit__(*sys.exc_info())
        _create_error_vectorstore_events(transaction, search_id, args, kwargs, linking_metadata, wrapped)
        raise
    ft.__exit__(None, None, None)

    if not response:
        return response

    _record_vector_search_success(transaction, linking_metadata, ft, search_id, args, kwargs, response, wrapped)
    return response


def wrap_similarity_search(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    search_id = str(uuid.uuid4())

    ft = FunctionTrace(name=wrapped.__name__, group="Llm/vectorstore/LangChain")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        response = wrapped(*args, **kwargs)
    except Exception:
        ft.notice_error(attributes={"vector_store_id": search_id})
        ft.__exit__(*sys.exc_info())
        _create_error_vectorstore_events(transaction, search_id, args, kwargs, linking_metadata, wrapped)
        raise
    ft.__exit__(None, None, None)

    if not response:
        return response

    _record_vector_search_success(transaction, linking_metadata, ft, search_id, args, kwargs, response, wrapped)
    return response


def _record_vector_search_success(transaction, linking_metadata, ft, search_id, args, kwargs, response, wrapped):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    bound_args = bind_args(wrapped, args, kwargs)
    request_query = bound_args["query"]
    request_k = bound_args["k"]
    duration = ft.duration * 1000
    response_number_of_documents = len(response)
    llm_metadata_dict = _get_llm_metadata(transaction)
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")

    llm_vector_search = {
        "request.k": request_k,
        "duration": duration,
        "response.number_of_documents": response_number_of_documents,
        "span_id": span_id,
        "trace_id": trace_id,
        "id": search_id,
        "vendor": "langchain",
        "ingest_source": "Python",
    }

    if settings.ai_monitoring.record_content.enabled:
        llm_vector_search["request.query"] = request_query

    llm_vector_search.update(llm_metadata_dict)
    transaction.record_custom_event("LlmVectorSearch", llm_vector_search)

    for index, doc in enumerate(response):
        sequence = index
        page_content = doc.page_content
        metadata = doc.metadata or {}

        metadata_dict = {f"metadata.{key}": value for key, value in metadata.items()}

        llm_vector_search_result = {
            "id": str(uuid.uuid4()),
            "search_id": search_id,
            "sequence": sequence,
            "span_id": span_id,
            "trace_id": trace_id,
            "vendor": "langchain",
            "ingest_source": "Python",
        }

        if settings.ai_monitoring.record_content.enabled:
            llm_vector_search_result["page_content"] = page_content
        llm_vector_search_result.update(metadata_dict)
        llm_vector_search_result.update(llm_metadata_dict)
        transaction.record_custom_event("LlmVectorSearchResult", llm_vector_search_result)


def wrap_tool_sync_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_id, agent_name, tool_input, tool_name, tool_run_id, run_args = _capture_tool_info(
        instance, wrapped, args, kwargs
    )

    # Filter out injected State or ToolRuntime arguments that would clog up the input
    try:
        filtered_tool_input = instance._filter_injected_args(tool_input)
    except Exception:
        filtered_tool_input = tool_input

    ft = FunctionTrace(name=f"{wrapped.__name__}/{tool_name}", group="Llm/tool/LangChain")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = wrapped(**run_args)
    except Exception:
        _record_tool_error(
            instance=instance,
            transaction=transaction,
            linking_metadata=linking_metadata,
            agent_name=agent_name,
            tool_id=tool_id,
            tool_input=filtered_tool_input,
            tool_name=tool_name,
            tool_run_id=tool_run_id,
            ft=ft,
        )
        raise
    ft.__exit__(None, None, None)

    if not return_val:
        return return_val

    _record_tool_success(
        instance=instance,
        transaction=transaction,
        linking_metadata=linking_metadata,
        agent_name=agent_name,
        tool_id=tool_id,
        tool_input=filtered_tool_input,
        tool_name=tool_name,
        tool_run_id=tool_run_id,
        ft=ft,
        response=return_val,
    )
    return return_val


async def wrap_tool_async_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    tool_id, agent_name, tool_input, tool_name, tool_run_id, run_args = _capture_tool_info(
        instance, wrapped, args, kwargs
    )

    # Filter out injected State or ToolRuntime arguments that would clog up the input
    try:
        filtered_tool_input = instance._filter_injected_args(tool_input)
    except Exception:
        filtered_tool_input = tool_input

    ft = FunctionTrace(name=f"{wrapped.__name__}/{tool_name}", group="Llm/tool/LangChain")
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = await wrapped(**run_args)
    except Exception:
        _record_tool_error(
            instance=instance,
            transaction=transaction,
            linking_metadata=linking_metadata,
            agent_name=agent_name,
            tool_id=tool_id,
            tool_input=filtered_tool_input,
            tool_name=tool_name,
            tool_run_id=tool_run_id,
            ft=ft,
        )
        raise
    ft.__exit__(None, None, None)

    if not return_val:
        return return_val

    _record_tool_success(
        instance=instance,
        transaction=transaction,
        linking_metadata=linking_metadata,
        agent_name=agent_name,
        tool_id=tool_id,
        tool_input=filtered_tool_input,
        tool_name=tool_name,
        tool_run_id=tool_run_id,
        ft=ft,
        response=return_val,
    )
    return return_val


def _capture_tool_info(instance, wrapped, args, kwargs):
    run_args = bind_args(wrapped, args, kwargs)

    tool_id = str(uuid.uuid4())
    metadata = run_args.get("metadata") or {}
    # lc_agent_name was added to metadata in LangChain 1.2.4
    agent_name = metadata.pop("_nr_agent_name", None) or metadata.get("lc_agent_name", None)
    tool_input = run_args.get("tool_input")
    tool_name = getattr(instance, "name", None)
    # Checking multiple places for an acceptable tool run ID, fallback to creating our own.
    tool_run_id = run_args.get("run_id", None) or run_args.get("tool_call_id", None) or str(uuid.uuid4())

    return tool_id, agent_name, tool_input, tool_name, tool_run_id, run_args


def _record_tool_success(
    instance, transaction, linking_metadata, agent_name, tool_id, tool_input, tool_name, tool_run_id, ft, response
):
    settings = transaction.settings if transaction.settings is not None else global_settings()

    full_tool_event_dict = {
        "id": tool_id,
        "run_id": tool_run_id,
        "name": tool_name,
        "agent_name": agent_name,
        "span_id": linking_metadata.get("span.id"),
        "trace_id": linking_metadata.get("trace.id"),
        "vendor": "langchain",
        "ingest_source": "Python",
        "duration": ft.duration * 1000,
    }

    result = None
    try:
        result = str(response.content) if hasattr(response, "content") else str(response)
    except Exception:
        _logger.debug("Failed to convert tool response into a string.\n%s", traceback.format_exception(*sys.exc_info()))
    if settings.ai_monitoring.record_content.enabled:
        full_tool_event_dict.update({"input": tool_input, "output": result})
    full_tool_event_dict.update(_get_llm_metadata(transaction))
    transaction.record_custom_event("LlmTool", full_tool_event_dict)


def _record_tool_error(
    instance, transaction, linking_metadata, agent_name, tool_id, tool_input, tool_name, tool_run_id, ft
):
    settings = transaction.settings if transaction.settings is not None else global_settings()
    ft.notice_error(attributes={"tool_id": tool_id})
    ft.__exit__(*sys.exc_info())

    # Make sure the builtin attributes take precedence over metadata attributes.
    error_tool_event_dict = {
        "id": tool_id,
        "run_id": tool_run_id,
        "name": tool_name,
        "agent_name": agent_name,
        "span_id": linking_metadata.get("span.id"),
        "trace_id": linking_metadata.get("trace.id"),
        "vendor": "langchain",
        "ingest_source": "Python",
        "duration": ft.duration * 1000,
        "error": True,
    }

    if settings.ai_monitoring.record_content.enabled:
        error_tool_event_dict["input"] = tool_input
    error_tool_event_dict.update(_get_llm_metadata(transaction))

    transaction.record_custom_event("LlmTool", error_tool_event_dict)


async def wrap_chain_async_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return await wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return await wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    run_args = bind_args(wrapped, args, kwargs)
    run_args["timestamp"] = int(1000.0 * time.time())
    completion_id = str(uuid.uuid4())
    add_nr_completion_id(run_args, completion_id)
    # Check to see if launched from agent or directly from chain.
    # The trace group will reflect from where it has started.
    # The AgentExecutor class has an attribute "agent" that does
    # not exist within the Chain class
    group_name = "Llm/agent/LangChain" if hasattr(instance, "agent") else "Llm/chain/LangChain"
    ft = FunctionTrace(name=wrapped.__name__, group=group_name)
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        response = await wrapped(input=run_args["input"], config=run_args["config"], **run_args.get("kwargs", {}))
    except Exception:
        ft.notice_error(attributes={"completion_id": completion_id})
        ft.__exit__(*sys.exc_info())
        _create_error_chain_run_events(
            transaction=transaction,
            instance=instance,
            run_args=run_args,
            completion_id=completion_id,
            linking_metadata=linking_metadata,
            duration=ft.duration * 1000,
        )
        raise
    ft.__exit__(None, None, None)

    if not response:
        return response

    _create_successful_chain_run_events(
        transaction=transaction,
        instance=instance,
        run_args=run_args,
        completion_id=completion_id,
        response=response,
        linking_metadata=linking_metadata,
        duration=ft.duration * 1000,
    )
    return response


def wrap_chain_sync_run(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    run_args = bind_args(wrapped, args, kwargs)
    run_args["timestamp"] = int(1000.0 * time.time())
    completion_id = str(uuid.uuid4())
    add_nr_completion_id(run_args, completion_id)
    # Check to see if launched from agent or directly from chain.
    # The trace group will reflect from where it has started.
    # The AgentExecutor class has an attribute "agent" that does
    # not exist within the Chain class
    group_name = "Llm/agent/LangChain" if hasattr(instance, "agent") else "Llm/chain/LangChain"
    ft = FunctionTrace(name=wrapped.__name__, group=group_name)
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        response = wrapped(input=run_args["input"], config=run_args["config"], **run_args.get("kwargs", {}))
    except Exception:
        ft.notice_error(attributes={"completion_id": completion_id})
        ft.__exit__(*sys.exc_info())
        _create_error_chain_run_events(
            transaction=transaction,
            instance=instance,
            run_args=run_args,
            completion_id=completion_id,
            linking_metadata=linking_metadata,
            duration=ft.duration * 1000,
        )
        raise
    ft.__exit__(None, None, None)

    if not response:
        return response

    _create_successful_chain_run_events(
        transaction=transaction,
        instance=instance,
        run_args=run_args,
        completion_id=completion_id,
        response=response,
        linking_metadata=linking_metadata,
        duration=ft.duration * 1000,
    )
    return response


def wrap_RunnableSequence_stream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    run_args = bind_args(wrapped, args, kwargs)
    run_args["timestamp"] = int(1000.0 * time.time())
    completion_id = str(uuid.uuid4())
    add_nr_completion_id(run_args, completion_id)
    # Check to see if launched from agent or directly from chain.
    # The trace group will reflect from where it has started.
    # The AgentExecutor class has an attribute "agent" that does
    # not exist within the Chain class
    group_name = "Llm/agent/LangChain" if hasattr(instance, "agent") else "Llm/chain/LangChain"
    ft = FunctionTrace(name=wrapped.__name__, group=group_name)
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = wrapped(input=run_args["input"], config=run_args["config"], **run_args.get("kwargs", {}))
        return_val = GeneratorProxy(
            return_val,
            on_stop_iteration=_on_chain_stop_iteration(
                ft=ft,
                instance=instance,
                run_args=run_args,
                completion_id=completion_id,
                response=[],
                linking_metadata=linking_metadata,
            ),
            on_error=_on_chain_error(
                ft=ft,
                instance=instance,
                run_args=run_args,
                completion_id=completion_id,
                linking_metadata=linking_metadata,
            ),
        )
    except Exception:
        _on_chain_error(
            ft=ft, instance=instance, run_args=run_args, completion_id=completion_id, linking_metadata=linking_metadata
        )(transaction)
        raise

    return return_val


def wrap_RunnableSequence_astream(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings if transaction.settings is not None else global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

    # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    run_args = bind_args(wrapped, args, kwargs)
    run_args["timestamp"] = int(1000.0 * time.time())
    completion_id = str(uuid.uuid4())
    add_nr_completion_id(run_args, completion_id)
    # Check to see if launched from agent or directly from chain.
    # The trace group will reflect from where it has started.
    # The AgentExecutor class has an attribute "agent" that does
    # not exist within the Chain class
    group_name = "Llm/agent/LangChain" if hasattr(instance, "agent") else "Llm/chain/LangChain"
    ft = FunctionTrace(name=wrapped.__name__, group=group_name)
    ft.__enter__()
    linking_metadata = get_trace_linking_metadata()
    try:
        return_val = wrapped(input=run_args["input"], config=run_args["config"], **run_args.get("kwargs", {}))
        return_val = AsyncGeneratorProxy(
            return_val,
            on_stop_iteration=_on_chain_stop_iteration(
                ft=ft,
                instance=instance,
                run_args=run_args,
                completion_id=completion_id,
                response=[],
                linking_metadata=linking_metadata,
            ),
            on_error=_on_chain_error(
                ft=ft,
                instance=instance,
                run_args=run_args,
                completion_id=completion_id,
                linking_metadata=linking_metadata,
            ),
        )
    except Exception:
        _on_chain_error(
            ft=ft, instance=instance, run_args=run_args, completion_id=completion_id, linking_metadata=linking_metadata
        )(transaction)
        raise

    return return_val


def _on_chain_stop_iteration(ft, instance, run_args, completion_id, response, linking_metadata):
    def _on_stop_iteration(proxy, transaction):
        ft.__exit__(None, None, None)
        _create_successful_chain_run_events(
            transaction=transaction,
            instance=instance,
            run_args=run_args,
            completion_id=completion_id,
            response=response,
            linking_metadata=linking_metadata,
            duration=ft.duration * 1000,
        )

    return _on_stop_iteration


def _on_chain_error(ft, instance, run_args, completion_id, linking_metadata):
    def _on_error(proxy, transaction):
        ft.notice_error(attributes={"completion_id": completion_id})
        ft.__exit__(*sys.exc_info())
        _create_error_chain_run_events(
            transaction=transaction,
            instance=instance,
            run_args=run_args,
            completion_id=completion_id,
            linking_metadata=linking_metadata,
            duration=ft.duration * 1000,
        )

    return _on_error


def add_nr_completion_id(run_args, completion_id):
    # invoke has an argument named "config" that contains metadata and tags.
    # Add the nr_completion_id into the metadata to be used as the function call
    # identifier when grabbing the run_id off the transaction.
    metadata = (run_args.get("config") or {}).get("metadata") or {}
    metadata["nr_completion_id"] = completion_id
    if not run_args.get("config"):
        run_args["config"] = {"metadata": metadata}
    else:
        run_args["config"]["metadata"] = metadata


def _create_error_chain_run_events(transaction, instance, run_args, completion_id, linking_metadata, duration):
    _input = run_args.get("input")
    llm_metadata_dict = _get_llm_metadata(transaction)
    run_id, metadata, tags = _get_run_manager_info(transaction, run_args, instance, completion_id)
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    input_message_list = [_input]

    # Make sure the builtin attributes take precedence over metadata attributes.
    full_chat_completion_summary_dict = {f"metadata.{key}": value for key, value in metadata.items()}
    full_chat_completion_summary_dict.update(
        {
            "id": completion_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": run_id,
            "duration": duration,
            "response.number_of_messages": len(input_message_list),
            "tags": tags,
            "error": True,
            "timestamp": run_args.get("timestamp") or None,
        }
    )
    full_chat_completion_summary_dict.update(llm_metadata_dict)
    transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)
    create_chat_completion_message_event(
        transaction,
        input_message_list,
        completion_id,
        span_id,
        trace_id,
        run_id,
        llm_metadata_dict,
        [],
        run_args["timestamp"] or None,
    )


def _get_run_manager_info(transaction, run_args, instance, completion_id):
    run_id = getattr(transaction, "_nr_chain_run_ids", {}).pop(completion_id, "")
    # metadata and tags are keys in the config parameter.
    metadata = {}
    metadata.update((run_args.get("config") or {}).get("metadata") or {})
    # Do not report internal nr_completion_id in metadata.
    metadata = {key: value for key, value in metadata.items() if key != "nr_completion_id"}
    tags = []
    tags.extend((run_args.get("config") or {}).get("tags") or [])
    return run_id, metadata, tags or None


def _get_llm_metadata(transaction):
    # Grab LLM-related custom attributes off of the transaction to store as metadata on LLM events
    custom_attrs_dict = transaction._custom_params
    llm_metadata_dict = {key: value for key, value in custom_attrs_dict.items() if key.startswith("llm.")}
    llm_context_attrs = getattr(transaction, "_llm_context_attrs", None)
    if llm_context_attrs:
        llm_metadata_dict.update(llm_context_attrs)

    return llm_metadata_dict


def _create_successful_chain_run_events(
    transaction, instance, run_args, completion_id, response, linking_metadata, duration
):
    _input = run_args.get("input")
    llm_metadata_dict = _get_llm_metadata(transaction)
    run_id, metadata, tags = _get_run_manager_info(transaction, run_args, instance, completion_id)
    span_id = linking_metadata.get("span.id")
    trace_id = linking_metadata.get("trace.id")
    input_message_list = [_input]
    output_message_list = []
    if isinstance(response, str):
        output_message_list = [response]
    else:
        try:
            output_message_list = [response[0]] if response else []
        except:
            try:
                output_message_list = [str(response)]
            except Exception:
                _logger.warning(
                    "Unable to capture response inside langchain chain instrumentation. No response message event will be captured. Report this issue to New Relic Support.\n%s",
                    traceback.format_exception(*sys.exc_info()),
                )

    # Make sure the builtin attributes take precedence over metadata attributes.
    full_chat_completion_summary_dict = {f"metadata.{key}": value for key, value in metadata.items()}
    full_chat_completion_summary_dict.update(
        {
            "id": completion_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "request_id": run_id,
            "duration": duration,
            "response.number_of_messages": len(input_message_list) + len(output_message_list),
            "tags": tags,
            "timestamp": run_args.get("timestamp") or None,
        }
    )

    if run_args.get("timestamp"):
        full_chat_completion_summary_dict["timestamp"] = run_args.get("timestamp")

    full_chat_completion_summary_dict.update(llm_metadata_dict)
    transaction.record_custom_event("LlmChatCompletionSummary", full_chat_completion_summary_dict)
    create_chat_completion_message_event(
        transaction,
        input_message_list,
        completion_id,
        span_id,
        trace_id,
        run_id,
        llm_metadata_dict,
        output_message_list,
        run_args["timestamp"] or None,
    )


def create_chat_completion_message_event(
    transaction,
    input_message_list,
    chat_completion_id,
    span_id,
    trace_id,
    run_id,
    llm_metadata_dict,
    output_message_list,
    request_timestamp=None,
):
    settings = transaction.settings if transaction.settings is not None else global_settings()

    # Loop through all input messages received from the create request and emit a custom event for each one
    for index, message in enumerate(input_message_list):
        chat_completion_input_message_dict = {
            "id": str(uuid.uuid4()),
            "request_id": run_id,
            "span_id": span_id,
            "trace_id": trace_id,
            "completion_id": chat_completion_id,
            "sequence": index,
            "vendor": "langchain",
            "ingest_source": "Python",
            "virtual_llm": True,
            "role": "user",  # default role for input messages, overridden by values in llm_metadata_dict
        }
        if settings.ai_monitoring.record_content.enabled:
            chat_completion_input_message_dict["content"] = message
        if request_timestamp:
            chat_completion_input_message_dict["timestamp"] = request_timestamp
        chat_completion_input_message_dict.update(llm_metadata_dict)
        transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_input_message_dict)

    if output_message_list:
        # Loop through all output messages received from the LLM response and emit a custom event for each one
        for index, message in enumerate(output_message_list):
            # Add offset of input_message_length so we don't receive any duplicate index values that match the input message IDs
            index += len(input_message_list)

            chat_completion_output_message_dict = {
                "id": str(uuid.uuid4()),
                "request_id": run_id,
                "span_id": span_id,
                "trace_id": trace_id,
                "completion_id": chat_completion_id,
                "sequence": index,
                "vendor": "langchain",
                "ingest_source": "Python",
                "is_response": True,
                "virtual_llm": True,
                "role": "assistant",  # default role for output messages, overridden by values in llm_metadata_dict
            }
            if settings.ai_monitoring.record_content.enabled:
                chat_completion_output_message_dict["content"] = message

            chat_completion_output_message_dict.update(llm_metadata_dict)
            transaction.record_custom_event("LlmChatCompletionMessage", chat_completion_output_message_dict)


def wrap_create_agent(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    settings = transaction.settings or global_settings()
    if not settings.ai_monitoring.enabled:
        return wrapped(*args, **kwargs)

        # Framework metric also used for entity tagging in the UI
    transaction.add_ml_model_info("LangChain", LANGCHAIN_VERSION)
    transaction._add_agent_attribute("llm", True)

    return_val = wrapped(*args, **kwargs)

    return AgentObjectProxy(return_val)


def wrap_StructuredTool_invoke(wrapped, instance, args, kwargs):
    """If StructuredTool.invoke is being run inside a ThreadPoolExecutor, propagate context from StructuredTool.ainvoke."""
    trace = current_trace()
    if trace:
        return wrapped(*args, **kwargs)

    metadata = bind_args(wrapped, args, kwargs).get("config", {}).get("metadata", {})
    # Delete the reference after grabbing it to avoid it ending up in LangChain attributes
    trace = metadata.pop("_nr_trace", None)
    if not trace:
        return wrapped(*args, **kwargs)

    with ContextOf(trace=trace):
        return wrapped(*args, **kwargs)


async def wrap_StructuredTool_ainvoke(wrapped, instance, args, kwargs):
    """Save a copy of the current trace if we're about to run StructuredTool.invoke inside a ThreadPoolExecutor."""
    trace = current_trace()
    # We only need to propagate for synchronous calls with an active trace
    if not trace or instance.coroutine:
        return await wrapped(*args, **kwargs)

    metadata = bind_args(wrapped, args, kwargs).get("config", {}).get("metadata", {})
    metadata["_nr_trace"] = trace

    try:
        return await wrapped(*args, **kwargs)
    finally:
        metadata.pop("_nr_trace", None)


def instrument_langchain_runnables_chains_base(module):
    if hasattr(module.RunnableSequence, "invoke"):
        wrap_function_wrapper(module, "RunnableSequence.invoke", wrap_chain_sync_run)
    if hasattr(module.RunnableSequence, "ainvoke"):
        wrap_function_wrapper(module, "RunnableSequence.ainvoke", wrap_chain_async_run)
    if hasattr(module.RunnableSequence, "stream"):
        wrap_function_wrapper(module, "RunnableSequence.stream", wrap_RunnableSequence_stream)
    if hasattr(module.RunnableSequence, "astream"):
        wrap_function_wrapper(module, "RunnableSequence.astream", wrap_RunnableSequence_astream)


def instrument_langchain_chains_base(module):
    if hasattr(module.Chain, "invoke"):
        wrap_function_wrapper(module, "Chain.invoke", wrap_chain_sync_run)
    if hasattr(module.Chain, "ainvoke"):
        wrap_function_wrapper(module, "Chain.ainvoke", wrap_chain_async_run)


def instrument_langchain_vectorstore_similarity_search(module):
    def _instrument_class(module, vector_class):
        if hasattr(getattr(module, vector_class, ""), "similarity_search"):
            wrap_function_wrapper(module, f"{vector_class}.similarity_search", wrap_similarity_search)
        if hasattr(getattr(module, vector_class, ""), "asimilarity_search"):
            wrap_function_wrapper(module, f"{vector_class}.asimilarity_search", wrap_asimilarity_search)

    vector_classes = VECTORSTORE_CLASSES.get(module.__name__)
    if vector_classes is None:
        return
    if isinstance(vector_classes, list):
        for vector_class in vector_classes:
            _instrument_class(module, vector_class)
    else:
        _instrument_class(module, vector_classes)


def instrument_langchain_core_tools(module):
    if hasattr(module.BaseTool, "run"):
        wrap_function_wrapper(module, "BaseTool.run", wrap_tool_sync_run)
    if hasattr(module.BaseTool, "arun"):
        wrap_function_wrapper(module, "BaseTool.arun", wrap_tool_async_run)


def instrument_langchain_core_runnables_config(module):
    if hasattr(module, "ContextThreadPoolExecutor"):
        wrap_function_wrapper(module, "ContextThreadPoolExecutor.submit", wrap_ContextThreadPoolExecutor_submit)


def instrument_langchain_core_tools_structured(module):
    if hasattr(module, "StructuredTool"):
        if hasattr(module.StructuredTool, "invoke"):
            wrap_function_wrapper(module, "StructuredTool.invoke", wrap_StructuredTool_invoke)
        if hasattr(module.StructuredTool, "ainvoke"):
            wrap_function_wrapper(module, "StructuredTool.ainvoke", wrap_StructuredTool_ainvoke)


def instrument_langchain_agents_factory(module):
    if hasattr(module, "create_agent"):
        wrap_function_wrapper(module, "create_agent", wrap_create_agent)
