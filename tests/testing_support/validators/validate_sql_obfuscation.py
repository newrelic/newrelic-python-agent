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

from newrelic.common.object_wrapper import transient_function_wrapper, function_wrapper


def validate_sql_obfuscation(expected_sqls):

    actual_sqls = []

    @transient_function_wrapper("newrelic.core.database_node", "DatabaseNode.__new__")
    def _validate_sql_obfuscation(wrapped, instance, args, kwargs):
        node = wrapped(*args, **kwargs)
        actual_sqls.append(node.formatted)
        return node

    @function_wrapper
    def _validate(wrapped, instance, args, kwargs):
        new_wrapper = _validate_sql_obfuscation(wrapped)
        result = new_wrapper(*args, **kwargs)

        for expected_sql in expected_sqls:
            assert expected_sql in actual_sqls, (expected_sql, actual_sqls)

        return result

    return _validate
