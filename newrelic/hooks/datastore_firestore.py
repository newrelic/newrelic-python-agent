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

from newrelic.api.datastore_trace import wrap_datastore_trace
from newrelic.api.function_trace import wrap_function_trace
from newrelic.common.async_wrapper import async_generator_wrapper, generator_wrapper


def _conn_str_to_host(getter):
    """Safely transform a getter that can retrieve a connection string into the resulting host."""

    def closure(obj, *args, **kwargs):
        try:
            return getter(obj, *args, **kwargs).split(":")[0]
        except Exception:
            return None

    return closure


def _conn_str_to_port(getter):
    """Safely transform a getter that can retrieve a connection string into the resulting port."""

    def closure(obj, *args, **kwargs):
        try:
            return getter(obj, *args, **kwargs).split(":")[1]
        except Exception:
            return None

    return closure


# Default Target ID and Instance Info
def _get_object_id(obj, *args, **kwargs):
    return getattr(obj, "id", None)


def _get_client_database_string(obj, *args, **kwargs):
    return getattr(getattr(obj, "_client", None), "_database_string", None)


def _get_client_target(obj, *args, **kwargs):
    return obj._client._target


_get_client_target_host = _conn_str_to_host(_get_client_target)
_get_client_target_port = _conn_str_to_port(_get_client_target)


# Client Instance Info
def _get_database_string(obj, *args, **kwargs):
    return getattr(obj, "_database_string", None)


def _get_target(obj, *args, **kwargs):
    return obj._target


_get_target_host = _conn_str_to_host(_get_target)
_get_target_port = _conn_str_to_port(_get_target)


# Query Target ID
def _get_parent_id(obj, *args, **kwargs):
    return getattr(getattr(obj, "_parent", None), "id", None)


# AggregationQuery Target ID
def _get_collection_ref_id(obj, *args, **kwargs):
    return getattr(getattr(obj, "_collection_ref", None), "id", None)


def instrument_google_cloud_firestore_v1_base_client(module):
    rollup = ("Datastore/all", "Datastore/Firestore/all")
    wrap_function_trace(
        module, "BaseClient.__init__", name=f"{module.__name__}:BaseClient.__init__", terminal=True, rollup=rollup
    )


def instrument_google_cloud_firestore_v1_client(module):
    if hasattr(module, "Client"):
        class_ = module.Client
        for method in ("collections", "get_all"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"Client.{method}",
                    operation=method,
                    product="Firestore",
                    target=None,
                    host=_get_target_host,
                    port_path_or_id=_get_target_port,
                    database_name=_get_database_string,
                    async_wrapper=generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_async_client(module):
    if hasattr(module, "AsyncClient"):
        class_ = module.AsyncClient
        for method in ("collections", "get_all"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncClient.{method}",
                    operation=method,
                    product="Firestore",
                    target=None,
                    host=_get_target_host,
                    port_path_or_id=_get_target_port,
                    database_name=_get_database_string,
                    async_wrapper=async_generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_collection(module):
    if hasattr(module, "CollectionReference"):
        class_ = module.CollectionReference
        for method in ("add", "get"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"CollectionReference.{method}",
                    product="Firestore",
                    target=_get_object_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("stream", "list_documents"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"CollectionReference.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_object_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_async_collection(module):
    if hasattr(module, "AsyncCollectionReference"):
        class_ = module.AsyncCollectionReference
        for method in ("add", "get"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncCollectionReference.{method}",
                    product="Firestore",
                    target=_get_object_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    operation=method,
                )

        for method in ("stream", "list_documents"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncCollectionReference.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_object_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=async_generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_document(module):
    if hasattr(module, "DocumentReference"):
        class_ = module.DocumentReference
        for method in ("create", "delete", "get", "set", "update"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"DocumentReference.{method}",
                    product="Firestore",
                    target=_get_object_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("collections",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"DocumentReference.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_object_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_async_document(module):
    if hasattr(module, "AsyncDocumentReference"):
        class_ = module.AsyncDocumentReference
        for method in ("create", "delete", "get", "set", "update"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncDocumentReference.{method}",
                    product="Firestore",
                    target=_get_object_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("collections",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncDocumentReference.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_object_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=async_generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_query(module):
    if hasattr(module, "Query"):
        class_ = module.Query
        for method in ("get",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"Query.{method}",
                    product="Firestore",
                    target=_get_parent_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("stream",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"Query.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_parent_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=generator_wrapper,
                )

    if hasattr(module, "CollectionGroup"):
        class_ = module.CollectionGroup
        for method in ("get_partitions",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"CollectionGroup.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_parent_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_async_query(module):
    if hasattr(module, "AsyncQuery"):
        class_ = module.AsyncQuery
        for method in ("get",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncQuery.{method}",
                    product="Firestore",
                    target=_get_parent_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("stream",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncQuery.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_parent_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=async_generator_wrapper,
                )

    if hasattr(module, "AsyncCollectionGroup"):
        class_ = module.AsyncCollectionGroup
        for method in ("get_partitions",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncCollectionGroup.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_parent_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=async_generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_aggregation(module):
    if hasattr(module, "AggregationQuery"):
        class_ = module.AggregationQuery
        for method in ("get",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AggregationQuery.{method}",
                    product="Firestore",
                    target=_get_collection_ref_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("stream",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AggregationQuery.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_collection_ref_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_async_aggregation(module):
    if hasattr(module, "AsyncAggregationQuery"):
        class_ = module.AsyncAggregationQuery
        for method in ("get",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncAggregationQuery.{method}",
                    product="Firestore",
                    target=_get_collection_ref_id,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )

        for method in ("stream",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncAggregationQuery.{method}",
                    operation=method,
                    product="Firestore",
                    target=_get_collection_ref_id,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                    async_wrapper=async_generator_wrapper,
                )


def instrument_google_cloud_firestore_v1_batch(module):
    if hasattr(module, "WriteBatch"):
        class_ = module.WriteBatch
        for method in ("commit",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"WriteBatch.{method}",
                    product="Firestore",
                    target=None,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )


def instrument_google_cloud_firestore_v1_async_batch(module):
    if hasattr(module, "AsyncWriteBatch"):
        class_ = module.AsyncWriteBatch
        for method in ("commit",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"AsyncWriteBatch.{method}",
                    product="Firestore",
                    target=None,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )


def instrument_google_cloud_firestore_v1_bulk_batch(module):
    if hasattr(module, "BulkWriteBatch"):
        class_ = module.BulkWriteBatch
        for method in ("commit",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    f"BulkWriteBatch.{method}",
                    product="Firestore",
                    target=None,
                    operation=method,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )


def instrument_google_cloud_firestore_v1_transaction(module):
    if hasattr(module, "Transaction"):
        class_ = module.Transaction
        for method in ("_commit", "_rollback"):
            if hasattr(class_, method):
                operation = method[1:]  # Trim leading underscore
                wrap_datastore_trace(
                    module,
                    f"Transaction.{method}",
                    product="Firestore",
                    target=None,
                    operation=operation,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )


def instrument_google_cloud_firestore_v1_async_transaction(module):
    if hasattr(module, "AsyncTransaction"):
        class_ = module.AsyncTransaction
        for method in ("_commit", "_rollback"):
            if hasattr(class_, method):
                operation = method[1:]  # Trim leading underscore
                wrap_datastore_trace(
                    module,
                    f"AsyncTransaction.{method}",
                    product="Firestore",
                    target=None,
                    operation=operation,
                    host=_get_client_target_host,
                    port_path_or_id=_get_client_target_port,
                    database_name=_get_client_database_string,
                )
