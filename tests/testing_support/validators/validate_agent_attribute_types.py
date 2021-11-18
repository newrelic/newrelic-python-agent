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

from newrelic.common.object_wrapper import transient_function_wrapper


def validate_agent_attribute_types(required_attrs):
    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_agent_attribute_types(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        attributes = transaction.agent_attributes
        attr_vals = {}
        for attr in attributes:
            attr_vals[attr.name] = attr.value

        for attr_name, attr_type in required_attrs.items():
            assert attr_name in attr_vals
            assert isinstance(attr_vals[attr_name], attr_type)

        return wrapped(*args, **kwargs)

    return _validate_agent_attribute_types
