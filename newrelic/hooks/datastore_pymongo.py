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

from newrelic.api.datastore_trace import wrap_datastore_trace
from newrelic.api.function_trace import wrap_function_trace

_pymongo_client_methods = (
    "save",
    "insert",
    "update",
    "drop",
    "remove",
    "find_one",
    "find",
    "count",
    "create_index",
    "ensure_index",
    "drop_indexes",
    "drop_index",
    "reindex",
    "index_information",
    "options",
    "group",
    "rename",
    "distinct",
    "map_reduce",
    "inline_map_reduce",
    "find_and_modify",
    "initialize_unordered_bulk_op",
    "initialize_ordered_bulk_op",
    "bulk_write",
    "insert_one",
    "insert_many",
    "replace_one",
    "update_one",
    "update_many",
    "delete_one",
    "delete_many",
    "find_raw_batches",
    "parallel_scan",
    "create_indexes",
    "list_indexes",
    "aggregate",
    "aggregate_raw_batches",
    "find_one_and_delete",
    "find_one_and_replace",
    "find_one_and_update",
)


def instrument_pymongo_pool(module):
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


def instrument_pymongo_mongo_client(module):
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


def instrument_pymongo_collection(module):
    # Exit early if this is a reimport of code from the newer module location
    moved_module = "pymongo.synchronous.collection"
    if module.__name__ != moved_module and moved_module in sys.modules:
        return

    def _collection_name(collection, *args, **kwargs):
        return collection.name

    for name in _pymongo_client_methods:
        if hasattr(module.Collection, name):
            wrap_datastore_trace(
                module, f"Collection.{name}", product="MongoDB", target=_collection_name, operation=name
            )
