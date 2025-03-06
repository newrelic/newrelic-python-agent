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
from testing_support.fixtures import catch_background_exceptions

"""
operation: method name
target: search argument
"""


def validate_datastore_trace_inputs(operation=None, target=None, host=None, port_path_or_id=None, database_name=None):
    @transient_function_wrapper("newrelic.api.datastore_trace", "DatastoreTrace.__init__")
    @catch_background_exceptions
    def _validate_datastore_trace_inputs(wrapped, instance, args, kwargs):
        def _bind_params(product, target, operation, host=None, port_path_or_id=None, database_name=None, **kwargs):
            return (product, target, operation, host, port_path_or_id, database_name, kwargs)

        (
            captured_product,
            captured_target,
            captured_operation,
            captured_host,
            captured_port_path_or_id,
            captured_database_name,
            captured_kwargs,
        ) = _bind_params(*args, **kwargs)

        if target is not None:
            assert captured_target == target, f"{captured_target} didn't match expected {target}"
        if operation is not None:
            assert captured_operation == operation, f"{captured_operation} didn't match expected {operation}"
        if host is not None:
            assert captured_host == host, f"{captured_host} didn't match expected {host}"
        if port_path_or_id is not None:
            assert captured_port_path_or_id == port_path_or_id, (
                f"{captured_port_path_or_id} didn't match expected {port_path_or_id}"
            )
        if database_name is not None:
            assert captured_database_name == database_name, (
                f"{captured_database_name} didn't match expected {database_name}"
            )

        return wrapped(*args, **kwargs)

    return _validate_datastore_trace_inputs
