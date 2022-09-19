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


def validate_distributed_trace_accepted(header="newrelic", transport_type="HTTP"):
    @function_wrapper
    def _validate_distributed_trace_accepted(wrapped, instance, args, kwargs):
        result = wrapped(*args, **kwargs)

        txn = current_transaction()

        assert txn
        assert txn._distributed_trace_state
        assert txn.parent_type == "App"
        assert txn._trace_id.startswith(txn.parent_tx)
        assert txn.parent_span is not None
        assert txn.parent_account == txn.settings.account_id
        assert txn.parent_transport_type == transport_type
        assert txn._priority is not None
        assert txn._sampled is not None

        return result

    return _validate_distributed_trace_accepted
