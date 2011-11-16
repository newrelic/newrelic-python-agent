import newrelic.api.background_task

def instrument_celery_app_task(module):

    def name_transaction_base_task_call(task, *args, **kwargs):
        return task.name

    newrelic.api.background_task.wrap_background_task(module,
            'BaseTask.__call__', name=name_transaction_base_task_call,
            group='Celery')
