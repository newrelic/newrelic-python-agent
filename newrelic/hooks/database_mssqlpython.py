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

from newrelic.api.database_trace import register_database_client
from newrelic.common.object_wrapper import wrap_object
from newrelic.hooks.database_dbapi2 import ConnectionFactory as DBAPI2ConnectionFactory
from newrelic.hooks.database_dbapi2 import ConnectionWrapper as DBAPI2ConnectionWrapper
from newrelic.hooks.database_dbapi2 import CursorWrapper as DBAPI2CursorWrapper


def instance_info(args, kwargs):
    try:
        connection_string = args[0]
        result = {}
        for token in connection_string.split(";"):
            if "=" in token:
                key, value = token.split("=")
                # Avoid storing passwords that are in the connection string.
                if key.lower() in ["server", "database"]:
                    result[key.lower()] = value

        server_string = result.get("server")

        if not server_string:
            host = port = None

        if server_string and (":" in server_string):
            server_string = server_string.split(":")[-1]

        if server_string and ("," in server_string):
            host, port = server_string.split(",")
        elif server_string:
            # Port was not specified
            host = server_string
            port = None

        database = result.get("database")
    except Exception:
        host = port = database = None

    return host, port, database
    

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


def instrument_mssqlpython(module):
    register_database_client(module, database_product="MSSQL", quoting_style="single", instance_info=instance_info)
    wrap_object(module, "connect", ConnectionFactory, (module,))
