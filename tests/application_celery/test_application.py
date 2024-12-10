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

from testing_support.validators.validate_code_level_metrics import (
    validate_code_level_metrics,
)
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.transaction import end_of_transaction, ignore_transaction


@validate_transaction_metrics(
    name="test_application:test_celery_task_as_function_trace",
    scoped_metrics=[("Function/_target_application.add", 1)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@background_task()
def test_celery_task_as_function_trace(application):
    """
    Calling add() inside a transaction means the agent will record
    add() as a FunctionTrace.

    """
    result = application.add(3, 4)
    assert result == 7


@validate_transaction_metrics(name="_target_application.add", group="Celery", scoped_metrics=[], background_task=True)
@validate_code_level_metrics("_target_application", "add")
def test_celery_task_as_background_task(application):
    """
    Calling add() outside of a transaction means the agent will create
    a background transaction (with a group of 'Celery') and record add()
    as a background task.

    """
    result = application.add(3, 4)
    assert result == 7


@validate_transaction_metrics(
    name="test_application:test_custom_celery_task_as_function_trace",
    scoped_metrics=[("Function/_target_application.custom_base_task_add", 1)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "custom_base_task_add")
@background_task()
def test_custom_celery_task_as_function_trace(application):
    """
    Calling custom_base_task_add() inside a transaction means the
    agent will record custom_base_task_add() as a FunctionTrace.

    """
    result = application.custom_base_task_add(3, 4)
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.custom_base_task_add", group="Celery", scoped_metrics=[], background_task=True
)
@validate_code_level_metrics("_target_application", "custom_base_task_add")
def test_custom_celery_task_as_background_task(application):
    """
    Calling custom_base_task_add() outside of a transaction means the agent will create
    a background transaction (with a group of 'Celery') and record custom_base_task_add()
    as a background task.

    """
    result = application.custom_base_task_add(3, 4)
    assert result == 7


@validate_transaction_metrics(
    name="test_application:test_custom_celery_task_as_function_trace",
    scoped_metrics=[("Function/_target_application.custom_base_task_with_super_add", 1)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "custom_base_task_with_super_add")
@background_task()
def test_custom_celery_task_with_super_as_function_trace(application):
    """
    Calling custom_base_task_with_super_add() inside a transaction means the
    agent will record custom_base_task_with_super_add() as a FunctionTrace.

    """
    result = application.custom_base_task_with_super_add(3, 4)
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.custom_base_task_with_super_add", group="Celery", scoped_metrics=[], background_task=True
)
@validate_code_level_metrics("_target_application", "custom_base_task_with_super_add")
def test_custom_celery_task_with_super_as_background_task(application):
    """
    Calling custom_base_task_with_super_add() outside of a transaction means the agent will create
    a background transaction (with a group of 'Celery') and record custom_base_task_with_super_add()
    as a background task.

    """
    result = application.custom_base_task_with_super_add(3, 4)
    assert result == 7


@validate_transaction_metrics(
    name="test_application:test_celery_tasks_multiple_function_traces",
    scoped_metrics=[("Function/_target_application.add", 1), ("Function/_target_application.tsum", 1)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "tsum")
@background_task()
def test_celery_tasks_multiple_function_traces(application):
    add_result = application.add(5, 6)
    assert add_result == 11

    tsum_result = application.tsum([1, 2, 3, 4])
    assert tsum_result == 10


@background_task()
def test_celery_tasks_ignore_transaction(application):
    """
    No transaction is recorded, due to the call to ignore_transaction(),
    so no validation fixture is used. The purpose of this test is to make
    sure the agent doesn't throw an error.
    """

    add_result = application.add(1, 2)
    assert add_result == 3

    ignore_transaction()

    tsum_result = application.tsum([1, 2, 3])
    assert tsum_result == 6


@validate_transaction_metrics(
    name="test_application:test_celery_tasks_end_transaction",
    scoped_metrics=[("Function/_target_application.add", 1)],
    background_task=True,
)
@background_task()
def test_celery_tasks_end_transaction(application):
    """
    Only functions that run before the call to end_of_transaction() are
    included in the transaction.
    """

    add_result = application.add(1, 2)
    assert add_result == 3

    end_of_transaction()

    tsum_result = application.tsum([1, 2, 3])
    assert tsum_result == 6


@validate_transaction_metrics(
    name="_target_application.nested_add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", 1)],
    background_task=True,
)
@validate_transaction_count(1)
@validate_code_level_metrics("_target_application", "nested_add")
def test_celery_nested_tasks(application):
    """
    Celery tasks run inside other celery tasks should not start a new transactions,
    and should create a function trace instead.
    """

    add_result = application.nested_add(1, 2)
    assert add_result == 3


@validate_transaction_metrics(
    name="_target_application.shared_task_add", group="Celery", scoped_metrics=[], background_task=True
)
@validate_code_level_metrics("_target_application", "shared_task_add")
def test_celery_shared_task_as_background_task(application):
    """
    Calling shared_task_add() outside of a transaction means the agent will create
    a background transaction (with a group of 'Celery') and record shared_task_add()
    as a background task.

    """
    result = application.shared_task_add(3, 4)
    assert result == 7
