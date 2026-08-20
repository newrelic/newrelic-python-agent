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


IGNORED_CLIENT_METHODS = {"client_connection"}

IGNORED_DATABASE_METHODS = {"client_connection", "database_link", "id"}

IGNORED_CONTAINER_METHODS = {
    "client_connection",
    "container_cache_lock",
    "container_link",
    "id",
    "is_system_key",
    "scripts",
}

IGNORED_ASYNC_CONTAINER_METHODS = {*IGNORED_CONTAINER_METHODS, "database_link"}

IGNORED_USER_METHODS = {"client_connection", "id", "user_link"}


def test_uninstrumented_client_methods(client):
    _uninstrumented_methods(client, IGNORED_CLIENT_METHODS)


def test_uninstrumented_async_client_methods(async_client):
    _uninstrumented_methods(async_client, IGNORED_CLIENT_METHODS)


def test_uninstrumented_database_methods(database):
    _uninstrumented_methods(database, IGNORED_DATABASE_METHODS)


def test_uninstrumented_async_database_methods(async_database):
    _uninstrumented_methods(async_database, IGNORED_DATABASE_METHODS)


def test_uninstrumented_container_methods(container):
    _uninstrumented_methods(container, IGNORED_CONTAINER_METHODS)


def test_uninstrumented_async_container_methods(async_container):
    _uninstrumented_methods(async_container, IGNORED_ASYNC_CONTAINER_METHODS)


def test_uninstrumented_user_methods(user):
    _uninstrumented_methods(user, IGNORED_USER_METHODS)


def test_uninstrumented_async_user_methods(async_user):
    _uninstrumented_methods(async_user, IGNORED_USER_METHODS)


def _uninstrumented_methods(db_object, ignored_methods):
    methods = {m for m in dir(db_object) if not m[0] == "_"}
    is_wrapped = lambda m: hasattr(getattr(db_object, m), "__wrapped__")
    uninstrumented = {m for m in methods - ignored_methods if not is_wrapped(m)}

    assert not uninstrumented, f"Uninstrumented methods: {sorted(uninstrumented)}"
