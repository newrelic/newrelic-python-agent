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

from newrelic.api.function_trace import FunctionTrace
import sys
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import (wrap_function_wrapper,
        function_wrapper)
from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import notice_error
from newrelic.api.wsgi_application import wrap_wsgi_application
from newrelic.api.function_trace import function_trace

from newrelic.api.web_transaction import WebTransaction, WebTransactionWrapper
from newrelic.api.application import application_instance

def wrap_execute(wrapped, instance, args, kwargs):
    name = "GraphQL"
    return WebTransactionWrapper(wrapped, application=application_instance(name))(*args, **kwargs)


def instrument_graphql_execute(module):
    wrap_function_wrapper(module, 'execute',
            wrap_execute)

