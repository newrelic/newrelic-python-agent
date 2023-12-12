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

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.time_trace import get_trace_linking_metadata
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

VECTORSTORE_CLASSES = [
    "AlibabaCloudOpenSearch",
    "AlibabaCloudOpenSearchSettings",
    "AnalyticDB",
    "Annoy",
    "AtlasDB",
    "AwaDB",
    "AzureSearch",
    "Bagel",
    "Cassandra",
    "AstraDB",
    "Chroma",
    "Clarifai",
    "Clickhouse",
    "ClickhouseSettings",
    "DashVector",
    "DatabricksVectorSearch",
    "DeepLake",
    "Dingo",
    "DocArrayHnswSearch",
    "DocArrayInMemorySearch",
    "ElasticKnnSearch",
    "ElasticVectorSearch",
    "ElasticsearchStore",
    "Epsilla",
    "FAISS",
    "Hologres",
    "LanceDB",
    "LLMRails",
    "Marqo",
    "MatchingEngine",
    "Meilisearch",
    "Milvus",
    "MomentoVectorIndex",
    "MongoDBAtlasVectorSearch",
    "MyScale",
    "MyScaleSettings",
    "Neo4jVector",
    "OpenSearchVectorSearch",
    "PGEmbedding",
    "PGVector",
    "Pinecone",
    "Qdrant",
    "Redis",
    "Rockset",
    "SKLearnVectorStore",
    "ScaNN",
    "SemaDB",
    "SingleStoreDB",
    "SQLiteVSS",
    "StarRocks",
    "SupabaseVectorStore",
    "Tair",
    "TileDB",
    "Tigris",
    "TimescaleVector",
    "Typesense",
    "USearch",
    "Vald",
    "Vearch",
    "Vectara",
    "VespaStore",
    "Weaviate",
    "Yellowbrick",
    "ZepVectorStore",
    "Zilliz",
    "TencentVectorDB",
    "AzureCosmosDBVectorSearch",
    "VectorStore",
]


def bind_similarity_search(query, k, *args, **kwargs):
    return query, k


def wrap_similarity_search(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    request_query, request_k = bind_similarity_search(*args, **kwargs)
    with DatastoreTrace(
        product="LangChain_vectorstore", target=request_query, operation="similarity_search", source=wrapped
    ) as dt:
        try:
            response = wrapped(*args, **kwargs)
        except Exception as exc:
            # Error logic goes here
            pass

    if not response:
        return response

    # LLMVectorSearch
    available_metadata = get_trace_linking_metadata()
    span_id = available_metadata.get("span.id", "")
    trace_id = available_metadata.get("trace.id", "")
    transaction_id = transaction.guid
    id = str(uuid.uuid4())
    request_query, request_k = bind_similarity_search(*args, **kwargs)
    duration = dt.duration
    response_number_of_documents = len(response)

    LLMVectorSearch_dict = {
        "span_id": span_id,
        "trace_id": trace_id,
        "transaction_id": transaction_id,
        "id": id,
        "vendor": "LangChain",
        "request.query": request_query,
        "request.k": request_k,
        "duration": duration,
        "response.number_of_documents": response_number_of_documents,
    }

    transaction.record_custom_event("LlmVectorSearch", LLMVectorSearch_dict)

    # LLMVectorSearchResult
    for index, doc in enumerate(response):
        search_id = str(uuid.uuid4())
        sequence = index
        page_content = getattr(response[0], "page_content", "")
        metadata = getattr(response[0], "metadata", "")

        metadata_dict = {}
        for key, value in metadata.items():
            new_key = "metadata.%s" % key
            metadata_dict[new_key] = value

        LLMVectorSearchResult_dict = {
            "search_id": search_id,
            "sequence": sequence,
            "page_content": page_content,
        }

        LLMVectorSearchResult_dict |= LLMVectorSearch_dict
        LLMVectorSearchResult_dict |= metadata_dict

        transaction.record_custom_event("LlmVectorSearchResult", LLMVectorSearchResult_dict)

    return response


def instrument_langchain_vectorstore_similarity_search(module):
    for vector_class in VECTORSTORE_CLASSES:
        if hasattr(module, vector_class):
            if hasattr(getattr(module, vector_class), "similarity_search"):
                wrap_function_wrapper(module, "%s.similarity_search" % vector_class, wrap_similarity_search)
