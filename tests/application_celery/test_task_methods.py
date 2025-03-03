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

import celery
import pytest
from _target_application import add, tsum
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_count import validate_transaction_count
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

FORGONE_TASK_METRICS = [("Function/_target_application.add", None), ("Function/_target_application.tsum", None)]


@pytest.fixture(scope="module", autouse=True, params=[False, True], ids=["unpatched", "patched"])
def with_worker_optimizations(request, celery_worker_available):
    if request.param:
        celery.app.trace.setup_worker_optimizations(celery_worker_available.app)

    yield request.param
    celery.app.trace.reset_worker_optimizations()


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    result = celery.chain(add.s(3, 4), add.s(5))()

    result = result.get()
    assert result == 12


@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    result = celery.group(add.s(3, 4), add.s(1, 2))()
    result = result.get()
    assert result == [7, 3]


@validate_transaction_metrics(
    name="_target_application.tsum",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
    background_task=True,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
    background_task=True,
    index=-2,
)
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=FORGONE_TASK_METRICS,
    rollup_metrics=FORGONE_TASK_METRICS,
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
    result = celery.chord([add.s(3, 4), add.s(1, 2)])(tsum.s())
    result = result.get()
    assert result == 10


@validate_transaction_metrics(
    name="celery.map/_target_application.tsum",
    group="Celery",
    scoped_metrics=[("Function/_target_application.tsum", 2)],
    rollup_metrics=[("Function/_target_application.tsum", 2)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "tsum", count=3)
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
    scoped_metrics=[("Function/_target_application.add", 2)],
    rollup_metrics=[("Function/_target_application.add", 2)],
    background_task=True,
)
@validate_code_level_metrics("_target_application", "add", count=3)
@validate_transaction_count(1)
def test_celery_task_starmap():
    """
    Executes starmap task on worker process with original task as a subtask and returns an AsyncResult.
    """
    result = add.starmap([(3, 4), (1, 2)]).apply_async()
    result = result.get()
    assert result == [7, 3]


@validate_transaction_metrics(
    name="celery.starmap/_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", 1)],
    rollup_metrics=[("Function/_target_application.add", 1)],
    background_task=True,
)
@validate_transaction_metrics(
    name="celery.starmap/_target_application.add",
    group="Celery",
    scoped_metrics=[("Function/_target_application.add", 1)],
    rollup_metrics=[("Function/_target_application.add", 1)],
    background_task=True,
    index=-2,
)
@validate_code_level_metrics("_target_application", "add", count=2)
@validate_code_level_metrics("_target_application", "add", count=2, index=-2)
@validate_transaction_count(2)
def test_celery_task_chunks():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = add.chunks([(3, 4), (1, 2)], n=1).apply_async()
    result = result.get()
    assert result == [[7], [3]]
