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

from newrelic.hooks.datastore_motor import _motor_client_async_methods, _motor_client_sync_methods

expected_motor_client_methods = set(_motor_client_async_methods) | set(_motor_client_sync_methods)

IGNORED_METHODS = {
    "codec_options",
    "database",
    "delegate",
    "full_name",
    "get_io_loop",
    "name",
    "read_concern",
    "read_preference",
    "with_options",
    "wrap",
    "write_concern",
}


def test_collection_uninstrumented_methods(client):
    # We cannot only test this by looking at the collection directly and ensuring the methods are wrapped, because the
    # underlying pymongo instrumentation will give us a false positive and nearly every method will show up as wrapped.
    # Instead, we compare the list of methods we expect to instrument as well as what was actually instrumented.
    # If either has a discrepancy, the test should fail.
    collection = client()["test"]["test"]
    methods = {m for m in dir(collection) if not m[0] == "_"} - IGNORED_METHODS

    # Check if any methods exist that we don't expect
    unexpected = methods - expected_motor_client_methods
    assert not unexpected, f"Uninstrumented methods: {sorted(unexpected)}"

    # Check what was actually instrumented
    is_wrapped = lambda m: hasattr(getattr(collection, m), "__wrapped__")
    uninstrumented = {m for m in methods if not is_wrapped(m)}
    assert not uninstrumented, f"Uninstrumented methods: {sorted(uninstrumented)}"
