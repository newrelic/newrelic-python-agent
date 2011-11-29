import newrelic.core.agent
import newrelic.api.application
import newrelic.api.background_task
import newrelic.api.pre_function

def instrument_celery_app_task(module):

    def name_transaction_base_task_call(task, *args, **kwargs):
        return task.name

    newrelic.api.background_task.wrap_background_task(module,
            'BaseTask.__call__', name=name_transaction_base_task_call,
            group='Celery')

def instrument_celery_worker(module):

    def activate_default_application(*args, **kwargs):
        application = newrelic.api.application.application()
        application.activate()

    newrelic.api.pre_function.wrap_pre_function(module,
        'process_initializer', activate_default_application)
