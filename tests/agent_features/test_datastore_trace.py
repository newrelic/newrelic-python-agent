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

from testing_support.validators.validate_datastore_trace_inputs import validate_datastore_trace_inputs

from newrelic.api.background_task import background_task
from newrelic.api.datastore_trace import DatastoreTrace, DatastoreTraceWrapper


@validate_datastore_trace_inputs(
    operation="test_operation",
    target="test_target",
    host="test_host",
    port_path_or_id="test_port",
    database_name="test_db_name",
)
@background_task()
def test_dt_trace_all_args():
    with DatastoreTrace(
        product="Agent Features",
        target="test_target",
        operation="test_operation",
        host="test_host",
        port_path_or_id="test_port",
        database_name="test_db_name",
    ):
        pass


@validate_datastore_trace_inputs(operation=None, target=None, host=None, port_path_or_id=None, database_name=None)
@background_task()
def test_dt_trace_empty():
    with DatastoreTrace(product=None, target=None, operation=None):
        pass


@background_task()
def test_dt_trace_callable_args():
    def product_callable():
        return "Agent Features"

    def target_callable():
        return "test_target"

    def operation_callable():
        return "test_operation"

    def host_callable():
        return "test_host"

    def port_path_id_callable():
        return "test_port"

    def db_name_callable():
        return "test_db_name"

    @validate_datastore_trace_inputs(
        operation="test_operation",
        target="test_target",
        host="test_host",
        port_path_or_id="test_port",
        database_name="test_db_name",
    )
    def _test():
        pass

    wrapped_fn = DatastoreTraceWrapper(
        _test,
        product=product_callable,
        target=target_callable,
        operation=operation_callable,
        host=host_callable,
        port_path_or_id=port_path_id_callable,
        database_name=db_name_callable,
    )
    wrapped_fn()
