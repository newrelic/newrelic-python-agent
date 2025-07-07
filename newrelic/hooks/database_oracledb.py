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
from newrelic.common.object_wrapper import ObjectProxy, wrap_object
from newrelic.hooks.database_dbapi2 import ConnectionFactory
from newrelic.hooks.database_dbapi2_async import AsyncConnectionFactory



def instance_info(args, kwargs):
    pass


def instrument_oracledb(module):
    register_database_client(module, database_product="Oracle", quoting_style="single+oracle")

    wrap_object(module, "connect", ConnectionFactory, (module,))
    wrap_object(module, "connect_async", AsyncConnectionFactory, (module,))
