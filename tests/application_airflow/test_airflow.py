import datetime

from airflow import settings
from airflow.models import DAG, TaskInstance
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.state import State

from testing_support.fixtures import validate_transaction_metrics

DEFAULT_DATE = datetime.datetime(2016, 1, 1)


@validate_transaction_metrics(
        name='test_task',
        scoped_metrics=[],
        background_task=True)
def test_airflow_dummy_operator():
    dag = DAG('test_airflow_dummy_operator', start_date=DEFAULT_DATE,
              end_date=DEFAULT_DATE + datetime.timedelta(days=10))
    task = DummyOperator(task_id='test_task', dag=dag)
    ti = TaskInstance(task=task, execution_date=datetime.datetime.now())
    ti.state = State.RUNNING
    session = settings.Session()
    session.merge(ti)
    session.commit()
    ti._run_raw_task()
