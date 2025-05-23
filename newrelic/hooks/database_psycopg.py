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

import inspect
import os
from urllib.parse import parse_qsl, unquote

from newrelic.api.database_trace import DatabaseTrace, register_database_client
from newrelic.api.function_trace import FunctionTrace
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import ObjectProxy, wrap_function_wrapper, wrap_object
from newrelic.hooks.database_dbapi2 import DEFAULT
from newrelic.hooks.database_dbapi2 import ConnectionFactory as DBAPI2ConnectionFactory
from newrelic.hooks.database_dbapi2 import ConnectionWrapper as DBAPI2ConnectionWrapper
from newrelic.hooks.database_dbapi2 import CursorWrapper as DBAPI2CursorWrapper
from newrelic.hooks.database_dbapi2_async import AsyncConnectionFactory as DBAPI2AsyncConnectionFactory
from newrelic.hooks.database_dbapi2_async import AsyncConnectionWrapper as DBAPI2AsyncConnectionWrapper
from newrelic.hooks.database_dbapi2_async import AsyncCursorWrapper as DBAPI2AsyncCursorWrapper
from newrelic.packages.urllib3 import util as ul3_util

# These functions return True if a non-default connection or cursor class is
# used. If the default connection and cursor are used without any unknown
# arguments, we can safely drop all cursor parameters to generate explain
# plans. Explain plans do not work with named cursors, so dropping the name
# allows explain plans to continue to function.
PsycopgConnection = None
PsycopgAsyncConnection = None


def should_preserve_connection_args(self, conninfo="", cursor_factory=None, **kwargs):
    try:
        if cursor_factory:
            return True

        return self._nr_last_object.__self__ not in (PsycopgConnection, PsycopgAsyncConnection)
    except Exception:
        pass

    return False


def should_preserve_cursor_args(
    name=None, binary=False, row_factory=None, scrollable=None, withhold=False, *args, **kwargs
):
    return bool(args or kwargs)


class CursorWrapper(DBAPI2CursorWrapper):
    def __enter__(self):
        self.__wrapped__.__enter__()

        # Must return a reference to self as otherwise will be
        # returning the inner cursor object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped cursor object and nothing will be
        # tracked.

        return self

    def execute(self, query, params=DEFAULT, *args, **kwargs):
        if hasattr(query, "as_string"):
            query = query.as_string(self)

        return super().execute(query, params, *args, **kwargs)

    def executemany(self, query, params_seq, *args, **kwargs):
        if hasattr(query, "as_string"):
            query = query.as_string(self)

        return super().executemany(query, params_seq, *args, **kwargs)


class ConnectionSaveParamsWrapper(DBAPI2ConnectionWrapper):
    __cursor_wrapper__ = CursorWrapper

    def execute(self, query, params=DEFAULT, *args, **kwargs):
        if hasattr(query, "as_string"):
            query = query.as_string(self)

        if params is not DEFAULT:
            with DatabaseTrace(
                sql=query,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=None,
                sql_parameters=params,
                execute_params=(args, kwargs),
                source=self.__wrapped__.execute,
            ):
                cursor = self.__wrapped__.execute(query, params, *args, **kwargs)
        else:
            with DatabaseTrace(
                sql=query,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=None,
                sql_parameters=None,
                execute_params=(args, kwargs),
                source=self.__wrapped__.execute,
            ):
                cursor = self.__wrapped__.execute(query, **kwargs)

        return self.__cursor_wrapper__(cursor, self._nr_dbapi2_module, self._nr_connect_params, (args, kwargs))

    def __enter__(self):
        name = callable_name(self.__wrapped__.__enter__)
        with FunctionTrace(name, source=self.__wrapped__.__enter__):
            self.__wrapped__.__enter__()

        # Must return a reference to self as otherwise will be
        # returning the inner connection object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped connection object and nothing will be
        # tracked.

        return self

    def __exit__(self, exc, value, tb):
        name = callable_name(self.__wrapped__.__exit__)
        with FunctionTrace(name, source=self.__wrapped__.__exit__):
            if exc is None:
                with DatabaseTrace(
                    sql="COMMIT",
                    dbapi2_module=self._nr_dbapi2_module,
                    connect_params=self._nr_connect_params,
                    source=self.__wrapped__.__exit__,
                ):
                    return self.__wrapped__.__exit__(exc, value, tb)
            else:
                with DatabaseTrace(
                    sql="ROLLBACK",
                    dbapi2_module=self._nr_dbapi2_module,
                    connect_params=self._nr_connect_params,
                    source=self.__wrapped__.__exit__,
                ):
                    return self.__wrapped__.__exit__(exc, value, tb)


# This connection wrapper does not save cursor parameters for explain plans. It
# is only used for the default connection class.
class ConnectionWrapper(ConnectionSaveParamsWrapper):
    def cursor(self, *args, **kwargs):
        # If any unknown cursor params are detected or a cursor factory is
        # used, store params for explain plans later.
        if should_preserve_cursor_args(*args, **kwargs):
            cursor_params = (args, kwargs)
        else:
            cursor_params = None

        return self.__cursor_wrapper__(
            self.__wrapped__.cursor(*args, **kwargs), self._nr_dbapi2_module, self._nr_connect_params, cursor_params
        )


class ConnectionFactory(DBAPI2ConnectionFactory):
    __connection_wrapper__ = ConnectionWrapper

    def __call__(self, *args, **kwargs):
        if should_preserve_connection_args(self, *args, **kwargs):
            self.__connection_wrapper__ = ConnectionSaveParamsWrapper

        return super().__call__(*args, **kwargs)


# Due to our explain plan feature requiring the use of synchronous DBAPI2 compliant modules, we can't support the use
# of AsyncConnection or any derivative to retrieve explain plans. There's also no longer a connection_factory argument
# on psycopg.connect() that was present in psycopg2, which affects the logic that attempted to use the same Connection
# class for explain plans. This is only relevant for users subclassing psycopg.Connection or psycopg.AsyncConnection.
# With no easy way to preserve or use the same class, and given that using the AsyncConnection class would never
# function with our explain plan feature, we always attempt to use the DBAPI2 compliant method of instantiating a new
# Connection, that being psycopg.connect(). That function is an alias of psycopg.Connection.connect(), and returns an
# instance of psycopg.Connection.
#
# Additionally, care is taken to preserve the cursor_factory argument and to use custom cursor classes. However, with
# AsyncConnection the compatible cursors will be async, which will not be compatible with the explain plan's
# synchronous Connection instance. To avoid this issue, we refuse to preserve the cursor_factory arument for
# AsyncConnection and instead fall back to using the default psycopg.Cursor class.
#
# This should allow the largest number of users to still have explain plans function for their applications, whether or
# not they are using AsyncConnection or custom classes. The issue of using a synchronous Connection object in an async
# application should be somewhat mitigated by the fact that our explain plan feature functions on the harvest thread.


class AsyncCursorWrapper(DBAPI2AsyncCursorWrapper):
    def __init__(self, cursor, dbapi2_module, connect_params, cursor_params):
        # Remove async cursor_factory so it doesn't interfere with sync Connections for explain plans
        args, kwargs = connect_params
        kwargs = dict(kwargs)
        kwargs.pop("cursor_factory", None)

        super().__init__(cursor, dbapi2_module, (args, kwargs), cursor_params)

    async def __aenter__(self):
        await self.__wrapped__.__aenter__()

        # Must return a reference to self as otherwise will be
        # returning the inner cursor object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped cursor object and nothing will be
        # tracked.

        return self

    async def execute(self, query, params=DEFAULT, *args, **kwargs):
        if hasattr(query, "as_string"):
            query = query.as_string(self)

        return await super().execute(query, params, *args, **kwargs)

    async def executemany(self, query, params_seq, *args, **kwargs):
        if hasattr(query, "as_string"):
            query = query.as_string(self)

        return await super().executemany(query, params_seq, *args, **kwargs)


class AsyncConnectionSaveParamsWrapper(DBAPI2AsyncConnectionWrapper):
    __cursor_wrapper__ = AsyncCursorWrapper

    async def execute(self, query, params=DEFAULT, *args, **kwargs):
        if hasattr(query, "as_string"):
            query = query.as_string(self)

        if params is not DEFAULT:
            with DatabaseTrace(
                sql=query,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=None,
                sql_parameters=params,
                execute_params=(args, kwargs),
                source=self.__wrapped__.execute,
            ):
                cursor = await self.__wrapped__.execute(query, params, *args, **kwargs)
        else:
            with DatabaseTrace(
                sql=query,
                dbapi2_module=self._nr_dbapi2_module,
                connect_params=self._nr_connect_params,
                cursor_params=None,
                sql_parameters=None,
                execute_params=(args, kwargs),
                source=self.__wrapped__.execute,
            ):
                cursor = await self.__wrapped__.execute(query, **kwargs)

        return self.__cursor_wrapper__(cursor, self._nr_dbapi2_module, self._nr_connect_params, (args, kwargs))

    async def __aenter__(self):
        name = callable_name(self.__wrapped__.__aenter__)
        with FunctionTrace(name, source=self.__wrapped__.__aenter__):
            await self.__wrapped__.__aenter__()

        # Must return a reference to self as otherwise will be
        # returning the inner connection object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped connection object and nothing will be
        # tracked.

        return self

    async def __aexit__(self, exc, value, tb):
        name = callable_name(self.__wrapped__.__aexit__)
        with FunctionTrace(name, source=self.__wrapped__.__aexit__):
            if exc is None:
                with DatabaseTrace(
                    sql="COMMIT",
                    dbapi2_module=self._nr_dbapi2_module,
                    connect_params=self._nr_connect_params,
                    source=self.__wrapped__.__aexit__,
                ):
                    return await self.__wrapped__.__aexit__(exc, value, tb)
            else:
                with DatabaseTrace(
                    sql="ROLLBACK",
                    dbapi2_module=self._nr_dbapi2_module,
                    connect_params=self._nr_connect_params,
                    source=self.__wrapped__.__aexit__,
                ):
                    return await self.__wrapped__.__aexit__(exc, value, tb)


# This connection wrapper does not save cursor parameters for explain plans. It
# is only used for the default connection class.
class AsyncConnectionWrapper(AsyncConnectionSaveParamsWrapper):
    def cursor(self, *args, **kwargs):
        # If any unknown cursor params are detected or a cursor factory is
        # used, store params for explain plans later.
        if should_preserve_cursor_args(*args, **kwargs):
            cursor_params = (args, kwargs)
        else:
            cursor_params = None

        return self.__cursor_wrapper__(
            self.__wrapped__.cursor(*args, **kwargs), self._nr_dbapi2_module, self._nr_connect_params, cursor_params
        )


class AsyncConnectionFactory(DBAPI2AsyncConnectionFactory):
    __connection_wrapper__ = AsyncConnectionWrapper

    async def __call__(self, *args, **kwargs):
        if should_preserve_connection_args(self, *args, **kwargs):
            self.__connection_wrapper__ = AsyncConnectionSaveParamsWrapper

        return await super().__call__(*args, **kwargs)


def instance_info(args, kwargs):
    p_host, p_hostaddr, p_port, p_dbname = _parse_connect_params(args, kwargs)
    host, port, db_name = _add_defaults(p_host, p_hostaddr, p_port, p_dbname)

    return (host, port, db_name)


def _parse_connect_params(args, kwargs):
    def _bind_params(conninfo=None, *args, **kwargs):
        return conninfo

    dsn = _bind_params(*args, **kwargs)

    try:
        if dsn and (dsn.startswith("postgres://") or dsn.startswith("postgresql://")):
            # Parse dsn as URI
            #
            # According to PGSQL, connect URIs are in the format of RFC 3896
            # https://www.postgresql.org/docs/9.5/static/libpq-connect.html

            parsed_uri = ul3_util.parse_url(dsn)

            host = parsed_uri.hostname or None
            host = host and unquote(host)

            # ipv6 brackets [] are contained in the URI hostname
            # and should be removed
            host = host and host.strip("[]")

            port = parsed_uri.port

            db_name = parsed_uri.path
            db_name = db_name and db_name.lstrip("/")
            db_name = db_name or None

            query = parsed_uri.query or ""
            qp = dict(parse_qsl(query))

            # Query parameters override hierarchical values in URI.

            host = qp.get("host") or host or None
            hostaddr = qp.get("hostaddr")
            port = qp.get("port") or port
            db_name = qp.get("dbname") or db_name

        elif dsn:
            # Parse dsn as a key-value connection string

            kv = dict([pair.split("=", 2) for pair in dsn.split()])
            host = kv.get("host")
            hostaddr = kv.get("hostaddr")
            port = kv.get("port")
            db_name = kv.get("dbname")

        else:
            # No dsn, so get the instance info from keyword arguments.

            host = kwargs.get("host")
            hostaddr = kwargs.get("hostaddr")
            port = kwargs.get("port")
            db_name = kwargs.get("dbname")

        # Ensure non-None values are strings.

        (host, hostaddr, port, db_name) = [str(s) if s is not None else s for s in (host, hostaddr, port, db_name)]

    except Exception:
        host = "unknown"
        hostaddr = "unknown"
        port = "unknown"
        db_name = "unknown"

    return (host, hostaddr, port, db_name)


def _add_defaults(parsed_host, parsed_hostaddr, parsed_port, parsed_database):
    # ENV variables set the default values

    parsed_host = parsed_host or os.environ.get("PGHOST")
    parsed_hostaddr = parsed_hostaddr or os.environ.get("PGHOSTADDR")
    parsed_port = parsed_port or os.environ.get("PGPORT")
    database = parsed_database or os.environ.get("PGDATABASE") or "default"

    # If hostaddr is present, we use that, since host is used for auth only.

    parsed_host = parsed_hostaddr or parsed_host

    if parsed_host is None:
        host = "localhost"
        port = "default"
    elif parsed_host.startswith("/"):
        host = "localhost"
        port = f"{parsed_host}/.s.PGSQL.{parsed_port or '5432'}"
    else:
        host = parsed_host
        port = parsed_port or "5432"

    return (host, port, database)


def wrapper_psycopg_as_string(wrapped, instance, args, kwargs):
    def _bind_params(context, *args, **kwargs):
        return context, args, kwargs

    context, _args, _kwargs = _bind_params(*args, **kwargs)

    # Unwrap the context for string conversion since psycopg uses duck typing
    # and a TypeError will be raised if a wrapper is used.
    if hasattr(context, "__wrapped__"):
        context = context.__wrapped__

    return wrapped(context, *_args, **_kwargs)


def wrap_Connection_connect(module):
    def _wrap_Connection_connect(wrapped, instance, args, kwargs):
        return ConnectionFactory(wrapped, module)(*args, **kwargs)

    return _wrap_Connection_connect


def wrap_AsyncConnection_connect(module):
    async def _wrap_AsyncConnection_connect(wrapped, instance, args, kwargs):
        return await AsyncConnectionFactory(wrapped, module)(*args, **kwargs)

    return _wrap_AsyncConnection_connect


def instrument_psycopg(module):
    global PsycopgConnection, PsycopgAsyncConnection

    PsycopgConnection = module.Connection
    PsycopgAsyncConnection = module.AsyncConnection

    register_database_client(
        module,
        database_product="Postgres",
        quoting_style="single+dollar",
        explain_query="explain",
        explain_stmts=("select", "insert", "update", "delete"),
        instance_info=instance_info,
    )

    if hasattr(module, "Connection"):
        if hasattr(module.Connection, "connect"):
            if not isinstance(module.Connection.connect, ObjectProxy):
                wrap_function_wrapper(module, "Connection.connect", wrap_Connection_connect(module))

    if hasattr(module, "connect"):
        if not isinstance(module.connect, ObjectProxy):
            wrap_object(module, "connect", ConnectionFactory, (module,))

    if hasattr(module, "AsyncConnection") and hasattr(module.AsyncConnection, "connect"):
        if not isinstance(module.AsyncConnection.connect, ObjectProxy):
            wrap_function_wrapper(module, "AsyncConnection.connect", wrap_AsyncConnection_connect(module))


def instrument_psycopg_sql(module):
    if hasattr(module, "Composable") and hasattr(module.Composable, "as_string"):
        for name, cls in inspect.getmembers(module):
            if not inspect.isclass(cls):
                continue

            if not issubclass(cls, module.Composable):
                continue

            wrap_function_wrapper(module, f"{name}.as_string", wrapper_psycopg_as_string)
