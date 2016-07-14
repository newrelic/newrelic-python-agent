import celery

from newrelic.agent import (background_task, ignore_transaction,
        end_of_transaction)
from newrelic.packages import six

from testing_support.fixtures import validate_transaction_metrics
from tasks import app, add, tsum


def select_python_version(py2, py3):
    return six.PY3 and py3 or py2


@validate_transaction_metrics(
        name='test_celery:test_celery_task_as_function_trace',
        scoped_metrics=select_python_version(
                py2=[('Function/tasks:add.__call__', 1)],
                py3=[('Function/celery.app.task:Task.__call__', 1)]
        ),
        background_task=True)
@background_task()
def test_celery_task_as_function_trace():
    """
    Calling add() inside a transaction means the agent will record
    add() as a FunctionTrace.

    """
    result = add(3, 4)
    assert result == 7


@validate_transaction_metrics(
        name='tasks.add',
        group='Celery',
        scoped_metrics=[],
        background_task=True)
def test_celery_task_as_background_task():
    """
    Calling add() outside of a transaction means the agent will create
    a background transaction (with a group of 'Celery') and record add()
    as a background task.

    """
    result = add(3, 4)
    assert result == 7


@validate_transaction_metrics(
        name='test_celery:test_celery_tasks_multiple_function_traces',
        scoped_metrics=select_python_version(
                py2=[('Function/tasks:add.__call__', 1),
                     ('Function/tasks:tsum.__call__', 1)
                ],
                py3=[('Function/celery.app.task:Task.__call__', 2)]
        ),
        background_task=True)
@background_task()
def test_celery_tasks_multiple_function_traces():
    add_result = add(5, 6)
    assert add_result == 11

    tsum_result = tsum([1, 2, 3, 4])
    assert tsum_result == 10

