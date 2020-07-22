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

import re

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.hooks import datastore_redis


def instrument_aredis_client(module):
    if hasattr(module, 'StrictRedis'):
        for name in datastore_redis._redis_client_methods:  # NOQA
            if name in vars(module.StrictRedis):
                datastore_redis._wrap_Redis_method_wrapper_(  # NOQA
                    module, 'StrictRedis', name
                )


def instrument_aredis_connection(module):
    wrap_function_wrapper(
        module,
        'Connection.send_command',
        datastore_redis._nr_Connection_send_command_wrapper_  # NOQA
    )
