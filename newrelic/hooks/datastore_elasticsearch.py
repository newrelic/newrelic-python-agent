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
from newrelic.api.transaction import current_transaction
from newrelic.common.function_signature_utils import bind_arguments
from newrelic.common.object_wrapper import function_wrapper, wrap_function_wrapper
from newrelic.packages import six

# An index name can be a string, None or a sequence. In the case of None
# an empty string or '*', it is the same as using '_all'. When a string
# it can also be a comma separated list of index names. A sequence
# obviously can also be more than one index name. Where we are certain
# there is only a single index name we use it, otherwise we use 'other'.


def wrap_elasticsearch_client_method(module, class_name, method_name, prefix=None):
    def _nr_wrapper_Elasticsearch_method_(wrapped, instance, args, kwargs):
        transaction = current_transaction()

        if transaction is None:
            return wrapped(*args, **kwargs)

        # When index is None, it means there is no target field
        # associated with this method. Hence this method will only
        # create an operation metric and no statement metric. This is
        # handled by setting the target to None when calling the
        # DatastoreTraceWrapper.

        index = bind_arguments(*args, **kwargs).get("index", None)
        if not index or index == "*":
            index = "_all"
        if not isinstance(index, six.string_types) or "," in index:
            index = "other"

        if prefix:
            operation = "%s.%s" % (prefix, method_name)
        else:
            operation = method_name

        transaction._nr_datastore_instance_info = (None, None, None)

        dt = DatastoreTrace(product="Elasticsearch", target=index, operation=operation, source=wrapped)

        with dt:
            result = wrapped(*args, **kwargs)

            instance_info = transaction._nr_datastore_instance_info
            host, port_path_or_id, _ = instance_info

            dt.host = host
            dt.port_path_or_id = port_path_or_id

            return result

    wrap_function_wrapper(module, "%s.%s" % (class_name, method_name), _nr_wrapper_Elasticsearch_method_)


_elasticsearch_client_methods = (
    "abort_benchmark",
    "benchmark",
    "bulk",
    "clear_scroll",
    "close",
    "close_point_in_time",
    "count",
    "count_percolate",
    "create",
    "delete",
    "delete_by_query",
    "delete_by_query_rethrottle",
    "delete_script",
    "delete_template",
    "exists",
    "exists_source",
    "explain",
    "field_caps",
    "get",
    "get_script",
    "get_script_context",
    "get_script_languages",
    "get_source",
    "get_template",
    "index",
    "info",
    "knn_search",
    "list_benchmarks",
    "mget",
    "mlt",
    "mpercolate",
    "msearch",
    "msearch_template",
    "mtermvectors",
    "open_point_in_time",
    "options",
    "percolate",
    "ping",
    "put_script",
    "put_template",
    "rank_eval",
    "reindex",
    "reindex_rethrottle",
    "render_search_template",
    "scripts_painless_execute",
    "scroll",
    "search",
    "search_exists",
    "search_mvt",
    "search_shards",
    "search_template",
    "suggest",
    "terms_enum",
    "termvector",
    "termvectors",
    "update",
    "update_by_query",
    "update_by_query_rethrottle",
)


def instrument_elasticsearch_client(module):
    for method_name in _elasticsearch_client_methods:
        if hasattr(getattr(module, "Elasticsearch"), method_name):
            wrap_elasticsearch_client_method(module, "Elasticsearch", method_name)


_elasticsearch_client_indices_methods = (
    "add_block",
    "analyze",
    "clear_cache",
    "clone",
    "close",
    "create",
    "create_data_stream",
    "data_streams_stats",
    "delete",
    "delete_alias",
    "delete_data_stream",
    "delete_index_template",
    "delete_template",
    "disk_usage",
    "downsample",
    "exists",
    "exists_alias",
    "exists_index_template",
    "exists_template",
    "field_usage_stats",
    "flush",
    "forcemerge",
    "get",
    "get_alias",
    "get_data_stream",
    "get_field_mapping",
    "get_index_template",
    "get_mapping",
    "get_settings",
    "get_template",
    "migrate_to_data_stream",
    "modify_data_stream",
    "open",
    "promote_data_stream",
    "put_alias",
    "put_index_template",
    "put_mapping",
    "put_settings",
    "put_template",
    "recovery",
    "refresh",
    "reload_search_analyzers",
    "resolve_index",
    "rollover",
    "segments",
    "shard_stores",
    "shrink",
    "simulate_index_template",
    "simulate_template",
    "split",
    "stats",
    "status",
    "unfreeze",
    "update_aliases",
    "validate_query",
)


def instrument_elasticsearch_client_indices(module):
    for method_name in _elasticsearch_client_indices_methods:
        if hasattr(getattr(module, "IndicesClient"), method_name):
            wrap_elasticsearch_client_method(module, "IndicesClient", method_name, "indices")


_elasticsearch_client_cat_methods = (
    "aliases",
    "allocation",
    "component_templates",
    "count",
    "fielddata",
    "health",
    "help",
    "indices",
    "master",
    "ml_data_frame_analytics",
    "ml_datafeeds",
    "ml_jobs",
    "ml_trained_models",
    "nodeattrs",
    "nodes",
    "pending_tasks",
    "plugins",
    "recovery",
    "repositories",
    "segments",
    "shards",
    "snapshots",
    "tasks",
    "templates",
    "thread_pool",
    "transforms",
)


def instrument_elasticsearch_client_cat(module):
    for method_name in _elasticsearch_client_cat_methods:
        if hasattr(getattr(module, "CatClient"), method_name):
            wrap_elasticsearch_client_method(module, "CatClient", method_name, "cat")


_elasticsearch_client_cluster_methods = (
    "allocation_explain",
    "delete_component_template",
    "delete_voting_config_exclusions",
    "exists_component_template",
    "get_component_template",
    "get_settings",
    "health",
    "pending_tasks",
    "post_voting_config_exclusions",
    "put_component_template",
    "put_settings",
    "remote_info",
    "reroute",
    "state",
    "stats",
)


def instrument_elasticsearch_client_cluster(module):
    for method_name in _elasticsearch_client_cluster_methods:
        if hasattr(getattr(module, "ClusterClient"), method_name):
            wrap_elasticsearch_client_method(module, "ClusterClient", method_name, "cluster")


_elasticsearch_client_nodes_methods = (
    "clear_repositories_metering_archive",
    "get_repositories_metering_info",
    "hot_threads",
    "info",
    "reload_secure_settings",
    "stats",
    "usage",
)


def instrument_elasticsearch_client_nodes(module):
    for method_name in _elasticsearch_client_nodes_methods:
        if hasattr(getattr(module, "NodesClient"), method_name):
            wrap_elasticsearch_client_method(module, "NodesClient", method_name, "nodes")


_elasticsearch_client_snapshot_methods = (
    "cleanup_repository",
    "clone",
    "create",
    "create_repository",
    "delete",
    "delete_repository",
    "get",
    "get_repository",
    "restore",
    "status",
    "verify_repository",
)


def instrument_elasticsearch_client_snapshot(module):
    for method_name in _elasticsearch_client_snapshot_methods:
        if hasattr(getattr(module, "SnapshotClient"), method_name):
            wrap_elasticsearch_client_method(module, "SnapshotClient", method_name, "snapshot")


_elasticsearch_client_tasks_methods = (
    "list",
    "cancel",
    "get",
)


def instrument_elasticsearch_client_tasks(module):
    for method_name in _elasticsearch_client_tasks_methods:
        if hasattr(getattr(module, "TasksClient"), method_name):
            wrap_elasticsearch_client_method(module, "TasksClient", method_name, "tasks")


_elasticsearch_client_ingest_methods = (
    "delete_pipeline",
    "geo_ip_stats",
    "get_pipeline",
    "processor_grok",
    "put_pipeline",
    "simulate",
)


def instrument_elasticsearch_client_ingest(module):
    for method_name in _elasticsearch_client_ingest_methods:
        if hasattr(getattr(module, "IngestClient"), method_name):
            wrap_elasticsearch_client_method(module, "IngestClient", method_name, "ingest")


#
# Instrumentation to get Datastore Instance Information
#


def _nr_Connection__init__wrapper(wrapped, instance, args, kwargs):
    """Cache datastore instance info on Connection object"""

    def _bind_params(host="localhost", port=9200, *args, **kwargs):
        return host, port

    host, port = _bind_params(*args, **kwargs)
    port = str(port)
    instance._nr_host_port = (host, port)

    return wrapped(*args, **kwargs)


def instrument_elasticsearch_connection_base(module):
    wrap_function_wrapper(module, "Connection.__init__", _nr_Connection__init__wrapper)


def BaseNode__init__wrapper(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)
    instance._nr_host_port = (instance.host, str(instance.port))
    return result


def instrument_elastic_transport__node__base(module):
    if hasattr(module, "BaseNode"):
        wrap_function_wrapper(module, "BaseNode.__init__", BaseNode__init__wrapper)


def _nr_get_connection_wrapper(wrapped, instance, args, kwargs):
    """Read instance info from Connection and stash on Transaction."""

    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    conn = wrapped(*args, **kwargs)

    instance_info = (None, None, None)
    try:
        tracer_settings = transaction.settings.datastore_tracer

        if tracer_settings.instance_reporting.enabled:
            host, port_path_or_id = conn._nr_host_port
            instance_info = (host, port_path_or_id, None)
    except Exception:
        instance_info = ("unknown", "unknown", None)

    transaction._nr_datastore_instance_info = instance_info

    return conn


def _nr_perform_request_wrapper(wrapped, instance, args, kwargs):
    """Read instance info from Connection and stash on Transaction."""

    transaction = current_transaction()

    if transaction is None:
        return wrapped(*args, **kwargs)

    if not hasattr(instance.node_pool.get, "_nr_wrapped"):
        instance.node_pool.get = function_wrapper(_nr_get_connection_wrapper)(instance.node_pool.get)
        instance.node_pool.get._nr_wrapped = True

    return wrapped(*args, **kwargs)


def instrument_elasticsearch_transport(module):
    if hasattr(module, "Transport") and hasattr(module.Transport, "get_connection"):
        wrap_function_wrapper(module, "Transport.get_connection", _nr_get_connection_wrapper)


def instrument_elastic_transport__transport(module):
    if hasattr(module, "Transport") and hasattr(module.Transport, "perform_request"):
        wrap_function_wrapper(module, "Transport.perform_request", _nr_perform_request_wrapper)
