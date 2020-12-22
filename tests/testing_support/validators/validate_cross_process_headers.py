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

from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import function_wrapper
from testing_support.validators.validate_distributed_tracing_header import \
    validate_distributed_tracing_header
from testing_support.validators.validate_outbound_headers import validate_outbound_headers


@function_wrapper
def validate_cross_process_headers(wrapped, instance, args, kwargs):
    result = wrapped(*args, **kwargs)

    transaction = current_transaction()
    settings = transaction.settings

    if settings.distributed_tracing.enabled:
        validate_distributed_tracing_header()
    else:
        validate_outbound_headers()

    return result
