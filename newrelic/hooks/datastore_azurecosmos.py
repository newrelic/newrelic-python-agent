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

import urllib.parse as urlparse

from newrelic.api.datastore_trace import DatastoreTrace, DatastoreTraceWrapper
from newrelic.api.transaction import current_transaction
from newrelic.common.async_wrapper import coroutine_wrapper
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args

##################################################
# Client Instrumentation
##################################################

# Synchronous functions for sync and async
_client_methods_sync_for_sync_and_async = (
    "from_connection_string",
    "get_database_client",
    "list_databases",
    "query_databases",
)

# Synchronous for sync, asynchronous for async
_client_methods_sync_async_respective = ("close", "create_database", "create_database_if_not_exists", "delete_database")

# Synchronous functions only with sync
_client_methods_sync = {"get_database_account"}

# Asyncronous functions only with async
_client_methods_async = ("_get_database_account",)


def wrap_CosmosClient_method_wrapper(module, name):
    def _wrap_CosmosClient_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        bound_args = bind_args(wrapped, args, kwargs)
        try:
            database_name = bound_args.get("database")
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, database_name = None, None, None

        with DatastoreTrace(
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=database_name,
            source=wrapped,
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.CosmosClient, name):
        wrap_function_wrapper(module, f"CosmosClient.{name}", _wrap_CosmosClient_method_wrapper_)


def wrap_aio_CosmosClient_method_wrapper(module, name):
    def _wrap_aio_CosmosClient_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        bound_args = bind_args(wrapped, args, kwargs)
        try:
            database_name = bound_args.get("database")
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, database_name = None, None, None

        return DatastoreTraceWrapper(
            wrapped,
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=database_name,
            async_wrapper=coroutine_wrapper,
        )(*args, **kwargs)

    if hasattr(module.CosmosClient, name):
        wrap_function_wrapper(module, f"CosmosClient.{name}", _wrap_aio_CosmosClient_method_wrapper_)


def instrument_cosmos_client(module):
    _methods = (*_client_methods_sync_for_sync_and_async, *_client_methods_sync, *_client_methods_sync_async_respective)
    for name in _methods:
        if hasattr(module, "CosmosClient"):
            wrap_CosmosClient_method_wrapper(module, name)


def instrument_cosmos_aio_client(module):
    _aio_methods = (*_client_methods_async, *_client_methods_sync_async_respective)
    for name in _aio_methods:
        if hasattr(module, "CosmosClient"):
            wrap_aio_CosmosClient_method_wrapper(module, name)

    _methods = _client_methods_sync_for_sync_and_async
    for name in _methods:
        if hasattr(module, "CosmosClient"):
            wrap_CosmosClient_method_wrapper(module, name)


##################################################
# Database Instrumentation
##################################################

# Synchronous functions for sync and async
_database_methods_sync_for_sync_and_async = (
    "get_container_client",
    "list_containers",
    "query_containers",
    "get_user_client",
    "list_users",
    "query_users",
)

# Synchronous for sync, asynchronous for async
_database_methods_sync_async_respective = (
    "read",
    "create_container",
    "create_container_if_not_exists",
    "replace_container",
    "delete_container",
    "create_user",
    "upsert_user",
    "replace_user",
    "delete_user",
    "get_throughput",
    "replace_throughput",
)

# Synchronous functions only with sync
_database_methods_sync = ("read_offer",)


def wrap_DatabaseProxy_method_wrapper(module, name):
    def _wrap_DatabaseProxy_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        try:
            database_link = instance.database_link
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, database_link = None, None, None

        with DatastoreTrace(
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=database_link,
            source=wrapped,
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.DatabaseProxy, name):
        wrap_function_wrapper(module, f"DatabaseProxy.{name}", _wrap_DatabaseProxy_method_wrapper_)


def wrap_aio_DatabaseProxy_method_wrapper(module, name):
    def _wrap_aio_DatabaseProxy_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        try:
            database_link = instance.database_link
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, database_link = None, None, None

        return DatastoreTraceWrapper(
            wrapped,
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=database_link,
            async_wrapper=coroutine_wrapper,
        )(*args, **kwargs)

    if hasattr(module.DatabaseProxy, name):
        wrap_function_wrapper(module, f"DatabaseProxy.{name}", _wrap_aio_DatabaseProxy_method_wrapper_)


def instrument_cosmos_database(module):
    _methods = (
        *_database_methods_sync_for_sync_and_async,
        *_database_methods_sync,
        *_database_methods_sync_async_respective,
    )
    for name in _methods:
        if hasattr(module, "DatabaseProxy"):
            wrap_DatabaseProxy_method_wrapper(module, name)


def instrument_cosmos_aio_database(module):
    _aio_methods = _database_methods_sync_async_respective
    for name in _aio_methods:
        if hasattr(module, "DatabaseProxy"):
            wrap_aio_DatabaseProxy_method_wrapper(module, name)

    _methods = _database_methods_sync_for_sync_and_async
    for name in _methods:
        if hasattr(module, "DatabaseProxy"):
            wrap_DatabaseProxy_method_wrapper(module, name)


##################################################
# Container Instrumentation
##################################################

# Synchronous functions for sync and async
_container_methods_sync_for_sync_and_async = (
    "read_all_items",
    "query_items_change_feed",
    "query_items",
    "list_conflicts",
    "query_conflicts",
    "read_feed_ranges",
)

# Synchronous for sync, asynchronous for async
_container_methods_sync_async_respective = (
    "read",
    "create_item",
    "read_item",
    "read_items",
    "semantic_rerank",
    "replace_item",
    "upsert_item",
    "patch_item",
    "delete_item",
    "get_throughput",
    "replace_throughput",
    "get_conflict",
    "delete_conflict",
    "delete_all_items_by_partition_key",
    "execute_item_batch",
    "get_latest_session_token",
    "feed_range_from_partition_key",
    "is_feed_range_subset",
)

# Synchronous functions only with sync
_container_methods_sync = ("read_offer",)


def wrap_ContainerProxy_method_wrapper(module, name):
    def _wrap_ContainerProxy_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        try:
            container_link = instance.container_link
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, container_link = None, None, None

        with DatastoreTrace(
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=container_link,
            source=wrapped,
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.ContainerProxy, name):
        wrap_function_wrapper(module, f"ContainerProxy.{name}", _wrap_ContainerProxy_method_wrapper_)


def wrap_aio_ContainerProxy_method_wrapper(module, name):
    def _wrap_aio_ContainerProxy_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        try:
            container_link = instance.container_link
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, container_link = None, None, None

        return DatastoreTraceWrapper(
            wrapped,
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=container_link,
            async_wrapper=coroutine_wrapper,
        )(*args, **kwargs)

    if hasattr(module.ContainerProxy, name):
        wrap_function_wrapper(module, f"ContainerProxy.{name}", _wrap_aio_ContainerProxy_method_wrapper_)


def instrument_cosmos_container(module):
    _methods = (
        *_container_methods_sync_for_sync_and_async,
        *_container_methods_sync,
        *_container_methods_sync_async_respective,
    )
    for name in _methods:
        if hasattr(module, "ContainerProxy"):
            wrap_ContainerProxy_method_wrapper(module, name)


def instrument_cosmos_aio_container(module):
    _aio_methods = _container_methods_sync_async_respective
    for name in _aio_methods:
        if hasattr(module, "ContainerProxy"):
            wrap_aio_ContainerProxy_method_wrapper(module, name)

    _methods = _container_methods_sync_for_sync_and_async
    for name in _methods:
        if hasattr(module, "ContainerProxy"):
            wrap_ContainerProxy_method_wrapper(module, name)


##################################################
# User Instrumentation
##################################################

# Synchronous functions for sync and async
_user_methods_sync_for_sync_and_async = ("list_permissions", "query_permissions")

# Synchronous for sync, asynchronous for async
_user_methods_sync_async_respective = (
    "read",
    "get_permission",
    "create_permission",
    "upsert_permission",
    "replace_permission",
    "delete_permission",
)


def wrap_UserProxy_method_wrapper(module, name):
    def _wrap_UserProxy_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        try:
            user_link = instance.user_link
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, user_link = None, None, None

        with DatastoreTrace(
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=user_link,
            source=wrapped,
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.UserProxy, name):
        wrap_function_wrapper(module, f"UserProxy.{name}", _wrap_UserProxy_method_wrapper_)


def wrap_aio_UserProxy_method_wrapper(module, name):
    def _wrap_aio_UserProxy_method_wrapper_(wrapped, instance, args, kwargs):
        transaction = current_transaction()
        if not transaction:
            return wrapped(*args, **kwargs)

        try:
            user_link = instance.user_link
            url = instance.client_connection.url_connection
            url_split = urlparse.urlsplit(url)
            host, port_path_or_id = url_split.netloc.split(":")
        except Exception:
            host, port_path_or_id, user_link = None, None, None

        return DatastoreTraceWrapper(
            wrapped,
            product="CosmosDB",
            target=None,
            operation=name,
            host=host,
            port_path_or_id=port_path_or_id,
            database_name=user_link,
            async_wrapper=coroutine_wrapper,
        )(*args, **kwargs)

    if hasattr(module.UserProxy, name):
        wrap_function_wrapper(module, f"UserProxy.{name}", _wrap_aio_UserProxy_method_wrapper_)


def instrument_cosmos_user(module):
    _methods = (*_user_methods_sync_for_sync_and_async, *_user_methods_sync_async_respective)
    for name in _methods:
        if hasattr(module, "UserProxy"):
            wrap_UserProxy_method_wrapper(module, name)


def instrument_cosmos_aio_user(module):
    _aio_methods = _user_methods_sync_async_respective
    for name in _aio_methods:
        if hasattr(module, "UserProxy"):
            wrap_aio_UserProxy_method_wrapper(module, name)

    _methods = _user_methods_sync_for_sync_and_async
    for name in _methods:
        if hasattr(module, "UserProxy"):
            wrap_UserProxy_method_wrapper(module, name)
