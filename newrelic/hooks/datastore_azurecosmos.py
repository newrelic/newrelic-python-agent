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

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.datastore_trace import wrap_datastore_trace
from newrelic.api.transaction import current_transaction
from newrelic.api.datastore_trace import DatastoreTrace
from newrelic.common.signature import bind_args
import urllib.parse as urlparse


_azure_cosmos_client_methods = {
    "close",
    "from_connection_string",
    "create_database",
    "create_database_if_not_exists",
    "get_database_client",
    "list_databases",
    "query_databases",
    "delete_databases",
    "get_database_account",
}

_azure_cosmos_database_methods = (
    "read",
    "create_container",
    "create_container_if_not_exists",
    "delete_container",
    "get_container_client",
    "list_containers",
    "query_containers",
    "replace_container",
    "list_users",
    "query_users",
    "get_user_client",
    "create_user",
    "upsert_user",
    "replace_user",
    "delete_user",
    "read_offer",
    "get_throughput",
    "replace_throughput",
)

_azure_cosmos_container_methods = {
    "read",
    "read_item",
    "read_items",
    "read_all_items",
    "query_items_change_feed",
    "query_items",
    "semantic_rerank",
    "replace_item",
    "upsert_item",
    "create_item",
    "patch_item",
    "execute_item_batch",
    "delete_item",
    "read_offer",
    "get_throughput",
    "replace_throughput",
    "list_conflicts",
    "query_conflicts",
    "get_conflict",
    "delete_conflict",
    "delete_all_items_by_partition_key",
    "read_feed_ranges",
    "get_latest_session_token",
    "feed_range_from_partition_key",
    "is_feed_range_subset",
}

_azure_cosmos_user_methods = {
    "read",
    "list_permissions",
    "query_permissions",
    "get_permission",
    "create_permission",
    "upsert_permission",
    "replace_permission",
    "delete_permission",
}


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
            product="CosmosDB", target=None, operation=name, host=host, port_path_or_id=port_path_or_id, database_name=database_name, source=wrapped
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.CosmosClient, name):
        wrap_function_wrapper(module, f"CosmosClient.{name}", _wrap_CosmosClient_method_wrapper_)


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
            product="CosmosDB", target=None, operation=name, host=host, port_path_or_id=port_path_or_id, database_name=database_link, source=wrapped
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.DatabaseProxy, name):
        wrap_function_wrapper(module, f"DatabaseProxy.{name}", _wrap_DatabaseProxy_method_wrapper_)


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
            product="CosmosDB", target=None, operation=name, host=host, port_path_or_id=port_path_or_id, database_name=container_link, source=wrapped
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.ContainerProxy, name):
        wrap_function_wrapper(module, f"ContainerProxy.{name}", _wrap_ContainerProxy_method_wrapper_)


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
            product="CosmosDB", target=None, operation=name, host=host, port_path_or_id=port_path_or_id, database_name=user_link, source=wrapped
        ):
            return wrapped(*args, **kwargs)

    if hasattr(module.UserProxy, name):
        wrap_function_wrapper(module, f"UserProxy.{name}", _wrap_UserProxy_method_wrapper_)


def instrument_cosmos_client(module):
    for name in _azure_cosmos_client_methods:
        if hasattr(module, "CosmosClient"):
            wrap_CosmosClient_method_wrapper(module, name)


def instrument_cosmos_database(module):
    for name in _azure_cosmos_database_methods:
        if hasattr(module, "DatabaseProxy"):
            wrap_DatabaseProxy_method_wrapper(module, name)


def instrument_cosmos_container(module):
    for name in _azure_cosmos_container_methods:
        if hasattr(module, "ContainerProxy"):
            wrap_ContainerProxy_method_wrapper(module, name)


def instrument_cosmos_user(module):
    for name in _azure_cosmos_user_methods:
        if hasattr(module, "UserProxy"):
            wrap_UserProxy_method_wrapper(module, name)

