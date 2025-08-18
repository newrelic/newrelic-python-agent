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

from _target_application import add, add_with_run, add_with_super, tsum
from celery import chain, chord, group
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_custom_parameters import validate_custom_parameters
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.background_task import background_task


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@validate_transaction_count(1)
def test_celery_task_call():
    """
    Executes task in local process and returns the result directly.
    """
    result = add(3, 4)
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@validate_transaction_count(1)
def test_celery_task_apply():
    """
    Executes task in local process and returns an EagerResult.
    """
    result = add.apply((3, 4))
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@validate_transaction_count(1)
def test_celery_task_delay():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add.delay(3, 4)
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@validate_transaction_count(1)
def test_celery_task_apply_async():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add.apply_async((3, 4))
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@validate_transaction_count(1)
def test_celery_app_send_task(celery_session_app):
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = celery_session_app.send_task("_target_application.add", (3, 4))
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add")
@validate_transaction_count(1)
def test_celery_task_signature():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add.s(3, 4).delay()
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add")
@validate_code_level_metrics("_target_application", "add", index=-2)
@validate_transaction_count(2)
def test_celery_task_link():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = add.apply_async((3, 4), link=[add.s(5)])
    result = result.get()
    assert result == 7  # Linked task result won't be returned


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add")
@validate_code_level_metrics("_target_application", "add", index=-2)
@validate_transaction_count(2)
def test_celery_chain():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = chain(add.s(3, 4), add.s(5))()

    result = result.get()
    assert result == 12


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add")
@validate_code_level_metrics("_target_application", "add", index=-2)
@validate_transaction_count(2)
def test_celery_group():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = group(add.s(3, 4), add.s(1, 2))()
    result = result.get()
    assert result == [7, 3]


@validate_transaction_metrics(
    name="_target_application.tsum",
    group="Celery",
    scoped_metrics=[("Function/_target_application.tsum", None)],
    rollup_metrics=[("Function/_target_application.tsum", None)],
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
    index=-2,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
    index=-3,
)
@validate_code_level_metrics("_target_application", "tsum")
@validate_code_level_metrics("_target_application", "add", index=-2)
@validate_code_level_metrics("_target_application", "add", index=-3)
@validate_transaction_count(3)
def test_celery_chord():
    """
    Executes 2 add tasks, followed by a tsum task on the worker process and returns an AsyncResult.
    """
    result = chord([add.s(3, 4), add.s(1, 2)])(tsum.s())
    result = result.get()
    assert result == 10


@validate_transaction_metrics(
    name="celery.map/_target_application.tsum",
    group="Celery",
    scoped_metrics=[("Function/_target_application.tsum", None)],
    rollup_metrics=[("Function/_target_application.tsum", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "tsum", count=1)
@validate_transaction_count(1)
def test_celery_task_map():
    """
    Executes map task on worker process with original task as a subtask and returns an AsyncResult.
    """
    result = tsum.map([(3, 4), (1, 2)]).apply()
    result = result.get()
    assert result == [7, 3]


@validate_transaction_metrics(
    name="celery.starmap/_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add", count=1)
@validate_transaction_count(1)
def test_celery_task_starmap():
    """
    Executes starmap task on worker process with original task as a subtask and returns an AsyncResult.
    """
    result = add.starmap([(3, 4), (1, 2)]).apply_async()
    result = result.get()
    assert result == [7, 3]


@validate_transaction_metrics(name="celery.starmap/_target_application.add", group="Celery", background_task=True)
@validate_transaction_metrics(
    name="celery.starmap/_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_transaction_metrics(
    name="celery.starmap/_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add", count=1)
@validate_code_level_metrics("_target_application", "add", count=1, index=-2)
@validate_transaction_count(2)
def test_celery_task_chunks():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = add.chunks([(3, 4), (1, 2)], n=1).apply_async()
    result = result.get()
    assert result == [[7], [3]]


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with super")])
@validate_transaction_metrics(
    name="_target_application.add_with_super",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_super", None)],
    rollup_metrics=[("Function/_target_application.add_with_super", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_super")
@validate_transaction_count(1)
def test_celery_task_call_custom_super():
    """
    Executes task in local process and returns the result directly.
    """
    result = add_with_super(3, 4)
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with super")])
@validate_transaction_metrics(
    name="_target_application.add_with_super",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_super", None)],
    rollup_metrics=[("Function/_target_application.add_with_super", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_super")
@validate_transaction_count(1)
def test_celery_task_apply_custom_super():
    """
    Executes task in local process and returns an EagerResult.
    """
    result = add_with_super.apply((3, 4))
    result = result.get()
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with super")])
@validate_transaction_metrics(
    name="_target_application.add_with_super",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_super", None)],
    rollup_metrics=[("Function/_target_application.add_with_super", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_super")
@validate_transaction_count(1)
def test_celery_task_delay_custom_super():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add_with_super.delay(3, 4)
    result = result.get()
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with super")])
@validate_transaction_metrics(
    name="_target_application.add_with_super",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_super", None)],
    rollup_metrics=[("Function/_target_application.add_with_super", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_super")
@validate_transaction_count(1)
def test_celery_task_apply_async_custom_super():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add_with_super.apply_async((3, 4))
    result = result.get()
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with run")])
@validate_transaction_metrics(
    name="_target_application.add_with_run",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_run", None)],
    rollup_metrics=[("Function/_target_application.add_with_run", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_run")
@validate_transaction_count(1)
def test_celery_task_call_custom_run():
    """
    Executes task in local process and returns the result directly.
    """
    result = add_with_run(3, 4)
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with run")])
@validate_transaction_metrics(
    name="_target_application.add_with_run",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_run", None)],
    rollup_metrics=[("Function/_target_application.add_with_run", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_run")
@validate_transaction_count(1)
def test_celery_task_apply_custom_run():
    """
    Executes task in local process and returns an EagerResult.
    """
    result = add_with_run.apply((3, 4))
    result = result.get()
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with run")])
@validate_transaction_metrics(
    name="_target_application.add_with_run",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_run", None)],
    rollup_metrics=[("Function/_target_application.add_with_run", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_run")
@validate_transaction_count(1)
def test_celery_task_delay_custom_run():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add_with_run.delay(3, 4)
    result = result.get()
    assert result == 7


@validate_custom_parameters(required_params=[("custom_task_attribute", "Called with run")])
@validate_transaction_metrics(
    name="_target_application.add_with_run",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_run", None)],
    rollup_metrics=[("Function/_target_application.add_with_run", None)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add_with_run")
@validate_transaction_count(1)
def test_celery_task_apply_async_custom_run():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add_with_run.apply_async((3, 4))
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", None)],
    rollup_metrics=[("Function/_target_application.add", None)],
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add_with_run",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_run", None)],
    rollup_metrics=[("Function/_target_application.add_with_run", None)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add")
@validate_code_level_metrics("_target_application", "add_with_run", index=-2)
@validate_transaction_count(2)
def test_celery_task_different_processes():
    """
    Executes two tasks, one in the main process and one in a worker process.
    """
    result = add_with_run.delay(3, 4)
    result = result.get()
    assert result == 7

    result = add.apply((3, 4))
    result = result.get()
    assert result == 7


@validate_transaction_metrics(
    name="test_task_methods:test_celery_task_in_transaction_different_processes",
    scoped_metrics=[("Function/_target_application.add", 1)],
    rollup_metrics=[("Function/_target_application.add", 1)],
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add_with_run",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add_with_run", None)],
    rollup_metrics=[("Function/_target_application.add_with_run", None)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add")
@validate_code_level_metrics("_target_application", "add_with_run", index=-2)
@validate_transaction_count(2)
@background_task()
def test_celery_task_in_transaction_different_processes():
    """
    This test demonstrates the limitations of the agent with regards
    to multiprocessing, namely when it involves transactions in a main
    process and worker processes.

    Two tasks are executed, one in the main process and one in a worker
    process.  A transaction (background task) is created in the context
    of the main process.  The worker process will not be aware of this
    transaction.

    The result is two transactions:
    1. Main process: Background task transaction with `add` task as a trace
    2. Worker process: `add_with_run` transaction with no additional traces
    """
    result = add_with_run.delay(3, 4)
    result = result.get()
    assert result == 7

    result = add.apply((3, 4))
    result = result.get()
    assert result == 7
