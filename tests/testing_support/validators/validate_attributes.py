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


def validate_attributes(attr_type, required_attr_names=None, forgone_attr_names=None):
    required_attr_names = required_attr_names or []
    forgone_attr_names = forgone_attr_names or []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_attributes(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        if attr_type == "intrinsic":
            attributes = transaction.trace_intrinsics
            attribute_names = attributes.keys()
        elif attr_type == "agent":
            attributes = transaction.agent_attributes
            attribute_names = [a.name for a in attributes]
            # validate that all agent attributes are included on the RootNode
            root_attribute_names = transaction.root.agent_attributes.keys()
            for name in attribute_names:
                assert name in root_attribute_names, name
        elif attr_type == "user":
            attributes = transaction.user_attributes
            attribute_names = [a.name for a in attributes]

            # validate that all user attributes are included on the RootNode
            root_attribute_names = transaction.root.user_attributes.keys()
            for name in attribute_names:
                assert name in root_attribute_names, name
        for name in required_attr_names:
            assert name in attribute_names, "name=%r, attributes=%r" % (name, attributes)

        for name in forgone_attr_names:
            assert name not in attribute_names, "name=%r, attributes=%r" % (name, attributes)

        return wrapped(*args, **kwargs)

    return _validate_attributes