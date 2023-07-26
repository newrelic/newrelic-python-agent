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

from newrelic.api.datastore_trace import DatastoreTrace, wrap_datastore_trace
from newrelic.api.function_trace import wrap_function_trace
from newrelic.common.async_wrapper import generator_wrapper
from newrelic.common.object_wrapper import wrap_function_wrapper


def _get_object_id(obj, *args, **kwargs):
    try:
        return obj.id
    except Exception:
        return None


def _get_parent_id(obj, *args, **kwargs):
    try:
        return obj._parent.id
    except Exception:
        return None


def _get_collection_ref_id(obj, *args, **kwargs):
    try:
        return obj._collection_ref.id
    except Exception:
        return None


def wrap_generator_method(module, class_name, method_name, target):
    def _wrapper(wrapped, instance, args, kwargs):
        target_ = target(instance) if callable(target) else target
        trace = DatastoreTrace(product="Firestore", target=target_, operation=method_name)
        wrapped = generator_wrapper(wrapped, trace)
        return wrapped(*args, **kwargs)

    class_ = getattr(module, class_name)
    if class_ is not None:
        if hasattr(class_, method_name):
            wrap_function_wrapper(module, "%s.%s" % (class_name, method_name), _wrapper)


def instrument_google_cloud_firestore_v1_base_client(module):
    rollup = ("Datastore/all", "Datastore/Firestore/all")
    wrap_function_trace(
        module, "BaseClient.__init__", name="%s:BaseClient.__init__" % module.__name__, terminal=True, rollup=rollup
    )


def instrument_google_cloud_firestore_v1_client(module):
    if hasattr(module, "Client"):
        class_ = module.Client
        for method in ("collections", "get_all"):
            if hasattr(class_, method):
                wrap_generator_method(module, "Client", method, target=None)


def instrument_google_cloud_firestore_v1_collection(module):
    if hasattr(module, "CollectionReference"):
        class_ = module.CollectionReference
        for method in ("add", "get"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    "CollectionReference.%s" % method,
                    product="Firestore",
                    target=_get_object_id,
                    operation=method,
                )

        for method in ("stream", "list_documents"):
            if hasattr(class_, method):
                wrap_generator_method(module, "CollectionReference", method, target=_get_object_id)


def instrument_google_cloud_firestore_v1_document(module):
    if hasattr(module, "DocumentReference"):
        class_ = module.DocumentReference
        for method in ("create", "delete", "get", "set", "update"):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    "DocumentReference.%s" % method,
                    product="Firestore",
                    target=_get_object_id,
                    operation=method,
                )

        for method in ("collections",):
            if hasattr(class_, method):
                wrap_generator_method(module, "DocumentReference", method, target=_get_object_id)


def instrument_google_cloud_firestore_v1_query(module):
    if hasattr(module, "Query"):
        class_ = module.Query
        for method in ("get",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module, "Query.%s" % method, product="Firestore", target=_get_parent_id, operation=method
                )

        for method in ("stream",):
            if hasattr(class_, method):
                wrap_generator_method(module, "Query", method, target=_get_parent_id)


def instrument_google_cloud_firestore_v1_aggregation(module):
    if hasattr(module, "AggregationQuery"):
        class_ = module.AggregationQuery
        for method in ("get",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module,
                    "AggregationQuery.%s" % method,
                    product="Firestore",
                    target=_get_collection_ref_id,
                    operation=method,
                )

        for method in ("stream",):
            if hasattr(class_, method):
                wrap_generator_method(module, "AggregationQuery", method, target=_get_collection_ref_id)


def instrument_google_cloud_firestore_v1_batch(module):
    if hasattr(module, "WriteBatch"):
        class_ = module.WriteBatch
        for method in ("commit",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module, "WriteBatch.%s" % method, product="Firestore", target=None, operation=method
                )


def instrument_google_cloud_firestore_v1_bulk_batch(module):
    if hasattr(module, "BulkWriteBatch"):
        class_ = module.BulkWriteBatch
        for method in ("commit",):
            if hasattr(class_, method):
                wrap_datastore_trace(
                    module, "BulkWriteBatch.%s" % method, product="Firestore", target=None, operation=method
                )


def instrument_google_cloud_firestore_v1_transaction(module):
    if hasattr(module, "Transaction"):
        class_ = module.Transaction
        for method in ("_commit", "_rollback"):
            if hasattr(class_, method):
                operation = method[1:]  # Trim leading underscore
                wrap_datastore_trace(
                    module, "Transaction.%s" % method, product="Firestore", target=None, operation=operation
                )
