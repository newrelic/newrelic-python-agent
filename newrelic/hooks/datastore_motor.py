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

from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.api.function_trace import wrap_function_trace
from newrelic.common.object_wrapper import wrap_function_wrapper

_motor_client_sync_methods = (
    "aggregate_raw_batches",
    "aggregate",
    "find_raw_batches",
    "find",
    "list_indexes",
    "list_search_indexes",
    "watch",
)

_motor_client_async_methods = (
    "bulk_write",
    "count_documents",
    "create_index",
    "create_indexes",
    "create_search_index",
    "create_search_indexes",
    "delete_many",
    "delete_one",
    "distinct",
    "drop_index",
    "drop_indexes",
    "drop_search_index",
    "drop",
    "estimated_document_count",
    "find_one_and_delete",
    "find_one_and_replace",
    "find_one_and_update",
    "find_one",
    "index_information",
    "insert_many",
    "insert_one",
    "options",
    "rename",
    "replace_one",
    "update_many",
    "update_one",
    "update_search_index",
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


def wrap_motor_method(module, class_name, method_name, is_async=False):
    cls = getattr(module, class_name)
    if not hasattr(cls, method_name):
        return

    # Define wrappers as closures to preserve method_name
    def _wrap_motor_method_sync(wrapped, instance, args, kwargs):
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

    async def _wrap_motor_method_async(wrapped, instance, args, kwargs):
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

    wrapper = _wrap_motor_method_async if is_async else _wrap_motor_method_sync
    wrap_function_wrapper(module, f"{class_name}.{method_name}", wrapper)


def instrument_motor_motor_asyncio(module):
    if hasattr(module, "AsyncIOMotorClient"):
        rollup = ("Datastore/all", "Datastore/MongoDB/all")
        # Name function explicitly as motor and pymongo have a history of overriding the
        # __getattr__() method in a way that breaks introspection.
        wrap_function_trace(
            module, "AsyncIOMotorClient.__init__", name=f"{module.__name__}:AsyncIOMotorClient.__init__", rollup=rollup
        )

    if hasattr(module, "AsyncIOMotorCollection"):
        for method_name in _motor_client_sync_methods:
            wrap_motor_method(module, "AsyncIOMotorCollection", method_name, is_async=False)
        for method_name in _motor_client_async_methods:
            wrap_motor_method(module, "AsyncIOMotorCollection", method_name, is_async=True)


def instrument_motor_motor_tornado(module):
    if hasattr(module, "MotorClient"):
        rollup = ("Datastore/all", "Datastore/MongoDB/all")
        # Name function explicitly as motor and pymongo have a history of overriding the
        # __getattr__() method in a way that breaks introspection.
        wrap_function_trace(
            module, "MotorClient.__init__", name=f"{module.__name__}:MotorClient.__init__", rollup=rollup
        )

    if hasattr(module, "MotorCollection"):
        for method_name in _motor_client_sync_methods:
            wrap_motor_method(module, "MotorCollection", method_name, is_async=False)
        for method_name in _motor_client_async_methods:
            wrap_motor_method(module, "MotorCollection", method_name, is_async=True)
