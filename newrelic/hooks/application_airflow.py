from newrelic.api.background_task import wrap_background_task
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction


class NewRelicStatsLogger(object):
    active = False

    @classmethod
    def record_custom_metric(cls, *args, **kwargs):
        if not cls.active:
            return

        transaction = current_transaction()
        application = application_instance()
        if transaction:
            record_custom_metric = transaction.record_custom_metric
        else:
            application.activate()
            record_custom_metric = application.record_custom_metric

        record_custom_metric(*args, **kwargs)

    @classmethod
    def incr(cls, stat, count=1, rate=1):
        cls.record_custom_metric(stat, count)

    @classmethod
    def decr(cls, stat, count=1, rate=1):
        pass

    @classmethod
    def gauge(cls, stat, value, rate=1, delta=False):
        cls.record_custom_metric(stat, value)

    @classmethod
    def timing(cls, stat, dt):
        cls.record_custom_metric(stat, dt)


def run_raw_task(wrapped, instance, args, kwargs):
    NewRelicStatsLogger.active = True
    return wrapped(*args, **kwargs)


def instrument_airflow_settings(module):
    from airflow import settings as airflow_settings
    airflow_settings.Stats = NewRelicStatsLogger


def extract_name(instance, *args, **kwargs):
    return instance.task.task_id


def instrument_airflow_taskinstance(module):
    wrap_background_task(module, 'TaskInstance._run_raw_task', name=extract_name)
    wrap_function_wrapper(module, 'TaskInstance._run_raw_task', run_raw_task)
