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

import sys

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.function_trace import wrap_function_trace
from newrelic.common.object_wrapper import wrap_function_wrapper

_pymongo_client_async_methods = (
    "aggregate",
    "aggregate_raw_batches",
    "bulk_write",
    "count_documents",
    "create_index",
    "create_indexes",
    "create_search_index",
    "create_search_indexes",
    "delete_many",
    "delete_one",
    "distinct",
    "drop",
    "drop_index",
    "drop_indexes",
    "drop_search_index",
    "estimated_document_count",
    "find_one",
    "find_one_and_delete",
    "find_one_and_replace",
    "find_one_and_update",
    "index_information",
    "insert_many",
    "insert_one",
    "list_indexes",
    "list_search_indexes",
    "options",
    "rename",
    "replace_one",
    "update_many",
    "update_one",
    "update_search_index",
    "watch",
)

_pymongo_client_sync_methods = (
    "find_raw_batches",
    "find",
    # Legacy methods from PyMongo 3
    "count",
    "ensure_index",
    "find_and_modify",
    "group",
    "initialize_ordered_bulk_op",
    "initialize_unordered_bulk_op",
    "inline_map_reduce",
    "insert",
    "map_reduce",
    "parallel_scan",
    "reindex",
    "remove",
    "save",
    "update",
)


def instance_info(collection):
    try:
        nodes = collection.database.client.nodes
        if len(nodes) == 1:
            return next(iter(nodes))
    except Exception:
        pass

    # If there are 0 nodes we're not currently connected, return nothing.
    # If there are 2+ nodes we're in a load balancing setup.
    # Unfortunately we can't rely on a deeper method to determine the actual server we're connected to in all cases.
    # We can't report more than 1 server for instance info, so we opt here to ignore reporting the host/port and
    # leave it empty to avoid confusing customers by guessing and potentially reporting the wrong server.
    return None, None


def wrap_pymongo_method(module, class_name, method_name, is_async=False):
    cls = getattr(module, class_name)
    if not hasattr(cls, method_name):
        return

    # Define wrappers as closures to preserve method_name
    def _wrap_pymongo_method_sync(wrapped, instance, args, kwargs):
        target = getattr(instance, "name", None)
        database_name = getattr(getattr(instance, "database", None), "name", None)
        with DatastoreTrace(
            product="MongoDB", target=target, operation=method_name, database_name=database_name
        ) as trace:
            response = wrapped(*args, **kwargs)

            # Gather instance info after response to ensure client is conncected
            address = instance_info(instance)
            trace.host = address[0]
            trace.port_path_or_id = address[1]

            return response

    async def _wrap_pymongo_method_async(wrapped, instance, args, kwargs):
        target = getattr(instance, "name", None)
        database_name = getattr(getattr(instance, "database", None), "name", None)
        with DatastoreTrace(
            product="MongoDB", target=target, operation=method_name, database_name=database_name
        ) as trace:
            response = await wrapped(*args, **kwargs)

            # Gather instance info after response to ensure client is conncected
            address = instance_info(instance)
            trace.host = address[0]
            trace.port_path_or_id = address[1]

            return response

    wrapper = _wrap_pymongo_method_async if is_async else _wrap_pymongo_method_sync
    wrap_function_wrapper(module, f"{class_name}.{method_name}", wrapper)


def instrument_pymongo_synchronous_pool(module):
    # Exit early if this is a reimport of code from the newer module location
    moved_module = "pymongo.synchronous.pool"
    if module.__name__ != moved_module and moved_module in sys.modules:
        return

    rollup = ("Datastore/all", "Datastore/MongoDB/all")

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    wrap_function_trace(
        module, "Connection.__init__", name=f"{module.__name__}:Connection.__init__", terminal=True, rollup=rollup
    )


def instrument_pymongo_asynchronous_pool(module):
    rollup = ("Datastore/all", "Datastore/MongoDB/all")

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    wrap_function_trace(
        module,
        "AsyncConnection.__init__",
        name=f"{module.__name__}:AsyncConnection.__init__",
        terminal=True,
        rollup=rollup,
    )


def instrument_pymongo_synchronous_mongo_client(module):
    # Exit early if this is a reimport of code from the newer module location
    moved_module = "pymongo.synchronous.mongo_client"
    if module.__name__ != moved_module and moved_module in sys.modules:
        return

    rollup = ("Datastore/all", "Datastore/MongoDB/all")

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    wrap_function_trace(
        module, "MongoClient.__init__", name=f"{module.__name__}:MongoClient.__init__", terminal=True, rollup=rollup
    )


def instrument_pymongo_asynchronous_mongo_client(module):
    rollup = ("Datastore/all", "Datastore/MongoDB/all")

    # Must name function explicitly as pymongo overrides the
    # __getattr__() method in a way that breaks introspection.

    wrap_function_trace(
        module,
        "AsyncMongoClient.__init__",
        name=f"{module.__name__}:AsyncMongoClient.__init__",
        terminal=True,
        rollup=rollup,
    )


def instrument_pymongo_synchronous_collection(module):
    # Exit early if this is a reimport of code from the newer module location
    moved_module = "pymongo.synchronous.collection"
    if module.__name__ != moved_module and moved_module in sys.modules:
        return

    if hasattr(module, "Collection"):
        for method_name in _pymongo_client_sync_methods:
            wrap_pymongo_method(module, "Collection", method_name, is_async=False)
        for method_name in _pymongo_client_async_methods:
            # Intentionally set is_async=False for sync collection
            wrap_pymongo_method(module, "Collection", method_name, is_async=False)


def instrument_pymongo_asynchronous_collection(module):
    if hasattr(module, "AsyncCollection"):
        for method_name in _pymongo_client_sync_methods:
            wrap_pymongo_method(module, "AsyncCollection", method_name, is_async=False)
        for method_name in _pymongo_client_async_methods:
            wrap_pymongo_method(module, "AsyncCollection", method_name, is_async=True)
