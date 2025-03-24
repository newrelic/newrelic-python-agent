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
    def _bind_params(host=None, user=None, passwd=None, db=None, port=None, *args, **kwargs):
        return host, port, db

    host, port, db = _bind_params(*args, **kwargs)

    return (host, port, db)


def instrument_pymysql(module):
    register_database_client(
        module,
        database_product="MySQL",
        quoting_style="single+double",
        explain_query="explain",
        explain_stmts=("select",),
        instance_info=instance_info,
    )

    # The names connect, Connect, and Connection all are aliases to the same connections.Connection() class.
    # We need to wrap each name separately since they are module level objects.
    for name in ("connect", "Connect", "Connection"):
        if hasattr(module, name):
            wrap_object(module, name, ConnectionFactory, (module,))
