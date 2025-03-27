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

import os

from newrelic.api.database_trace import register_database_client
from newrelic.common.object_wrapper import wrap_object
from newrelic.hooks.database_dbapi2 import ConnectionFactory as DBAPI2ConnectionFactory
from newrelic.hooks.database_dbapi2 import ConnectionWrapper as DBAPI2ConnectionWrapper
from newrelic.hooks.database_dbapi2 import CursorWrapper as DBAPI2CursorWrapper


class CursorWrapper(DBAPI2CursorWrapper):
    def __enter__(self):
        self.__wrapped__.__enter__()
        return self


class ConnectionWrapper(DBAPI2ConnectionWrapper):
    __cursor_wrapper__ = CursorWrapper

    def __enter__(self):
        self.__wrapped__.__enter__()
        return self


class ConnectionFactory(DBAPI2ConnectionFactory):
    __connection_wrapper__ = ConnectionWrapper


def instance_info(args, kwargs):
    def _bind_params(
        host=None,
        user=None,
        password=None,
        database=None,
        port=None,
        unix_socket=None,
        conv=None,
        connect_timeout=None,
        compress=None,
        named_pipe=None,
        init_command=None,
        read_default_file=None,
        read_default_group=None,
        *args,
        **kwargs,
    ):
        # db allowed as an alias for database, but only in kwargs
        if "db" in kwargs:
            database = kwargs["db"]
        return (host, port, database, unix_socket, read_default_file, read_default_group)

    params = _bind_params(*args, **kwargs)
    host, port, database, unix_socket, read_default_file, read_default_group = params
    explicit_host = host

    port_path_or_id = None
    if read_default_file or read_default_group:
        host = host or "default"
        port_path_or_id = "unknown"
    elif not host:
        host = "localhost"

    if host == "localhost":
        # precedence: explicit -> cnf (if used) -> env -> 'default'
        port_path_or_id = unix_socket or port_path_or_id or os.getenv("MYSQL_UNIX_PORT", "default")
    elif explicit_host:
        # only reach here if host is explicitly passed in
        port = port and str(port)
        # precedence: explicit -> cnf (if used) -> env -> '3306'
        port_path_or_id = port or port_path_or_id or os.getenv("MYSQL_TCP_PORT", "3306")

    # There is no default database if omitted from the connect params
    # In this case, we should report unknown
    database = database or "unknown"

    return (host, port_path_or_id, database)


def instrument_mysqldb(module):
    register_database_client(
        module,
        database_product="MySQL",
        quoting_style="single+double",
        explain_query="explain",
        explain_stmts=("select",),
        instance_info=instance_info,
    )

    # The names connect, Connection, and Connect all are aliases to the same Connect() function.
    # We need to wrap each name separately since they are module level objects.
    for name in ("connect", "Connection", "Connect"):
        if hasattr(module, name):
            wrap_object(module, name, ConnectionFactory, (module,))
