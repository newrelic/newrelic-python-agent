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


from _target_application import add, tsum
from celery import chain, chord, group
from conftest import skip_if_py2
from testing_support.validators.validate_transaction_count import (
    validate_transaction_count,
)
from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

TASK_METRICS = [("Function/_target_application.add", 1)]


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    # scoped_metrics=TASK_METRICS,
    # rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(1)
def test_celery_task_call():
    """
    Executes task in local process and returns the result directly.
    """
    result = add(3, 4)
    assert result == 7


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=TASK_METRICS,
    rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(1)
def test_celery_task_apply():
    """
    Executes task in local process and returns an EagerResult.
    """
    result = add.apply((3, 4))
    result = result.get()
    assert result == 7


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=TASK_METRICS,
    rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(1)
def test_celery_task_delay():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add.delay(3, 4)
    result = result.get()
    assert result == 7


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=TASK_METRICS,
    rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(1)
def test_celery_task_apply_async():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add.apply_async((3, 4))
    result = result.get()
    assert result == 7


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=TASK_METRICS,
    rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(1)
def test_celery_app_send_task(celery_session_app):
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = celery_session_app.send_task("_target_application.add", (3, 4))
    result = result.get()
    assert result == 7


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    scoped_metrics=TASK_METRICS,
    rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(1)
def test_celery_task_signature():
    """
    Executes task on worker process and returns an AsyncResult.
    """
    result = add.s(3, 4).delay()
    result = result.get()
    assert result == 7


@skip_if_py2
# @validate_transaction_metrics(
#     name="_target_application.add",
#     group="Celery",
#     # scoped_metrics=TASK_METRICS,
#     # rollup_metrics=TASK_METRICS,
#     background_task=True,
# )
@validate_transaction_count(2)
def test_celery_task_link():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = add.apply_async((3, 4), link=[add.s(5)])
    result = result.get()
    assert result == 7  # Linked task result won't be returned


@skip_if_py2
@validate_transaction_metrics(
    name="_target_application.add",
    group="Celery",
    # scoped_metrics=TASK_METRICS,
    # rollup_metrics=TASK_METRICS,
    background_task=True,
)
@validate_transaction_count(2)
def test_celery_chain():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = chain(add.s(3, 4), add.s(5))()

    result = result.get()
    assert result == 12


@skip_if_py2
# @validate_transaction_metrics(
#     name="_target_application.add",
#     group="Celery",
#     # scoped_metrics=TASK_METRICS,
#     # rollup_metrics=TASK_METRICS,
#     background_task=True,
# )
@validate_transaction_count(2)
def test_celery_group():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = group(add.s(3, 4), add.s(1, 2))()
    result = result.get()
    assert result == [7, 3]


@skip_if_py2
# @validate_transaction_metrics(
#     name="_target_application.add",
#     group="Celery",
#     # scoped_metrics=TASK_METRICS,
#     # rollup_metrics=TASK_METRICS,
#     background_task=True,
# )
@validate_transaction_count(3)
def test_celery_chord():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = chord([add.s(3, 4), add.s(1, 2)])(tsum.s())
    result = result.get()
    assert result == 10


@skip_if_py2
# @validate_transaction_metrics(
#     name="_target_application.add",
#     group="Celery",
#     # scoped_metrics=TASK_METRICS,
#     # rollup_metrics=TASK_METRICS,
#     background_task=True,
# )
@validate_transaction_count(1)
def test_celery_task_map():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = tsum.map([(3, 4), (1, 2)]).apply()
    result = result.get()
    assert result == [7, 3]


@skip_if_py2
# @validate_transaction_metrics(
#     name="_target_application.add",
#     group="Celery",
#     # scoped_metrics=TASK_METRICS,
#     # rollup_metrics=TASK_METRICS,
#     background_task=True,
# )
@validate_transaction_count(1)
def test_celery_task_starmap():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = add.starmap([(3, 4), (1, 2)]).apply_async()
    result = result.get()
    assert result == [7, 3]


@skip_if_py2
# @validate_transaction_metrics(
#     name="_target_application.add",
#     group="Celery",
#     # scoped_metrics=TASK_METRICS,
#     # rollup_metrics=TASK_METRICS,
#     background_task=True,
# )
@validate_transaction_count(2)
def test_celery_task_chunks():
    """
    Executes multiple tasks on worker process and returns an AsyncResult.
    """
    result = add.chunks([(3, 4), (1, 2)], n=1).apply_async()
    result = result.get()
    assert result == [[7], [3]]
