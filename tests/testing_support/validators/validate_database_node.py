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

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_database_node(validator):

    # Accepts one argument, a function that itself takes one argument: the
    # node. The validator should raise an exception if the node is not correct.

    nodes = []

    @transient_function_wrapper('newrelic.core.database_node',
            'DatabaseNode.__new__')
    def _validate_explain_plan(wrapped, instance, args, kwargs):
        node = wrapped(*args, **kwargs)
        nodes.append(node)
        return node

    @function_wrapper
    def _validate(wrapped, instance, args, kwargs):
        new_wrapper = _validate_explain_plan(wrapped)
        result = new_wrapper(*args, **kwargs)

        for node in nodes:
            validator(node)

        return result

    return _validate
