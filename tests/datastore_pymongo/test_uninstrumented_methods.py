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

import pytest
from testing_support.db_settings import mongodb_settings

from newrelic.common.package_version_utils import get_package_version_tuple

# Skip if AsyncMongoClient has not been implemented yet
if get_package_version_tuple("pymongo") < (4, 9, 0):
    # PyMongo 3.0-4.8
    from pymongo.mongo_client import MongoClient

    # Bypass the fact that there's only 1 client class
    AsyncMongoClient = MongoClient
else:
    # PyMongo 4.9+
    from pymongo.asynchronous.mongo_client import AsyncMongoClient
    from pymongo.synchronous.mongo_client import MongoClient


DB_SETTINGS = mongodb_settings()[0]
MONGODB_HOST = DB_SETTINGS["host"]
MONGODB_PORT = DB_SETTINGS["port"]
MONGODB_COLLECTION = DB_SETTINGS["collection"]

IGNORED_METHODS = {
    "codec_options",
    "database",
    "full_name",
    "name",
    "next",
    "read_concern",
    "read_preference",
    "with_options",
    "write_concern",
}


@pytest.mark.parametrize("client_cls", [MongoClient, AsyncMongoClient])
def test_sync_collection_uninstrumented_methods(client_cls):
    client = client_cls(MONGODB_HOST, MONGODB_PORT)
    collection = client["test"]["test"]
    methods = {m for m in dir(collection) if not m[0] == "_"} - IGNORED_METHODS

    is_wrapped = lambda m: hasattr(getattr(collection, m), "__wrapped__")
    uninstrumented = {m for m in methods if not is_wrapped(m)}
    assert not uninstrumented, f"Uninstrumented methods: {sorted(uninstrumented)}"
