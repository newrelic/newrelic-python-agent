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

import newrelic.api.function_trace

from newrelic.hooks import nosql_redis


def instrument_aredis_connection(module):
    newrelic.api.function_trace.wrap_function_trace(
        module, 'Connection.connect'
    )


def instrument_aredis_client(module):
    if hasattr(module, 'StrictRedis'):
        for method in nosql_redis._methods_1 + nosql_redis._methods_2:  # NOQA
            if hasattr(module.StrictRedis, method):
                newrelic.api.function_trace.wrap_function_trace(
                        module, 'StrictRedis.%s' % method
                )
