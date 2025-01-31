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

from newrelic.api.database_trace import DatabaseTrace, register_database_client
from newrelic.api.function_trace import wrap_function_trace
from newrelic.api.time_trace import current_trace
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args

DBAPI2_MODULE = None
DEFAULT = object()


def wrap_Session_execute(wrapped, instance, args, kwargs):
    # Most of this wrapper is lifted from DBAPI2 wrappers, which can't be used
    # directly since Cassandra doesn't actually conform to DBAPI2.

    trace = current_trace()
    if not trace or trace.terminal_node():
        # Exit early there's no transaction, or if we're under an existing DatabaseTrace
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)

    sql_parameters = bound_args.get("parameters", None)

    sql = bound_args.get("query", None)
    if not isinstance(sql, str):
        statement = getattr(sql, "prepared_statement", sql)  # Unbind BoundStatement
        sql = getattr(statement, "query_string", statement)  # Unpack query from SimpleStatement and PreparedStatement

    database_name = getattr(instance, "keyspace", None)

    host = None
    port = None
    try:
        contact_points = instance.cluster.contact_points
        if len(contact_points) == 1:
            contact_point = next(iter(contact_points))
            if isinstance(contact_point, str):
                host = contact_point
                port = instance.cluster.port
            elif isinstance(contact_point, tuple):
                host, port = contact_point
            else:  # Handle cassandra.connection.Endpoint types
                host = contact_point.address
                port = contact_point.port
    except Exception:
        pass

    if sql_parameters is not DEFAULT:
        with DatabaseTrace(
            sql=sql,
            sql_parameters=sql_parameters,
            execute_params=(args, kwargs),
            host=host,
            port_path_or_id=port,
            database_name=database_name,
            dbapi2_module=DBAPI2_MODULE,
            source=wrapped,
        ):
            return wrapped(*args, **kwargs)
    else:
        with DatabaseTrace(
            sql=sql,
            execute_params=(args, kwargs),
            host=host,
            port_path_or_id=port,
            database_name=database_name,
            dbapi2_module=DBAPI2_MODULE,
            source=wrapped,
        ):
            return wrapped(*args, **kwargs)


def instrument_cassandra(module):
    # Cassandra isn't DBAPI2 compliant, but we need the DatabaseTrace to function properly. We can set parameters
    # for CQL parsing and the product name here, and leave the explain plan functionality unused.
    global DBAPI2_MODULE
    DBAPI2_MODULE = module

    register_database_client(
        module,
        database_product="Cassandra",
        quoting_style="single+double",
        explain_query=None,
        explain_stmts=(),
        instance_info=None,  # Already handled in wrappers
    )


def instrument_cassandra_cluster(module):
    if hasattr(module, "Session"):
        # Cluster connect instrumentation, normally supplied by DBAPI2ConnectionFactory
        wrap_function_trace(
            module, "Cluster.connect", terminal=True, rollup=["Datastore/all", "Datastore/Cassandra/all"]
        )

        # Currently Session.execute() is a wrapper for calling Session.execute_async() and immediately waiting for
        # the result. We therefore need to instrument Session.execute() in order to get timing information for sync
        # query executions. We also need to instrument Session.execute_async() to at least get metrics for async
        # queries, but we can't get timing information from that alone. We also need to add an early exit condition
        # for when instrumentation for Session.execute_async() is called within Session.execute().
        wrap_function_wrapper(module, "Session.execute", wrap_Session_execute)

        # This wrapper only provides metrics, and not proper timing for async queries as they are distributed across
        # potentially many threads at once. This is left uninstrumented for the time being.
        wrap_function_wrapper(module, "Session.execute_async", wrap_Session_execute)
