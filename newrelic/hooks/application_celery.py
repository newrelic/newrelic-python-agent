"""This module provides instrumentation for Celery. Has been tested on
Celery versions 2.2.X through 2.5.X.

Note that Celery has a habit of moving things around in code base or of
completely rewriting stuff across minor versions. See additional notes
about this below.

"""

import functools

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTaskWrapper
from newrelic.api.pre_function import wrap_pre_function

def instrument_celery_app_task(module):

    # Triggered for both 'celery.app.task' and 'celery.task.base'.

    if hasattr(module, 'BaseTask'):

        # Need to add a wrapper for background task entry point.

	# In Celery 2.2 the 'BaseTask' class actually resided in the
	# module 'celery.task.base'. In Celery 2.3 the 'BaseTask' class
	# moved to 'celery.app.task' but an alias to it was retained in
	# the module 'celery.task.base'. We need to detect both module
	# imports, but we check the module name associated with
	# 'BaseTask' to ensure that we do not instrument the class via
	# the alias in Celery 2.3 and later.

	# In Celery 2.5+, although 'BaseTask' still exists execution of
	# the task doesn't pass through it. For Celery 2.5+ need to wrap
	# the tracer instead.

        def task_name(task, *args, **kwargs):
            return task.name

        if module.BaseTask.__module__ == module.__name__:
            module.BaseTask.__call__ = BackgroundTaskWrapper(
                    module.BaseTask.__call__, name=task_name,
                    group='Celery')

def instrument_celery_execute_trace(module):

    # Triggered for 'celery.execute_trace'.

    if hasattr(module, 'build_tracer'):

	# Need to add a wrapper for background task entry point.

        # In Celery 2.5+ we need to wrap the task when tracer is being
        # created. Note that in Celery 2.5 the 'build_tracer' function
        # actually resided in the module 'celery.execute.task'. In
        # Celery 3.0 the 'build_tracer' function moved to
        # 'celery.task.trace'.

        _build_tracer = module.build_tracer

        def build_tracer(name, task, *args, **kwargs):
            task = task or module.tasks[name]
            task = BackgroundTaskWrapper(task, name=name, group='Celery')
            return _build_tracer(name, task, *args, **kwargs)

        module.build_tracer = build_tracer

def instrument_celery_worker(module):

    # Triggered for 'celery.worker' and 'celery.concurrency.processes'.

    if hasattr(module, 'process_initializer'):

        # We try and force registration of default application after
        # fork of worker process rather than lazily on first request.

	# Originally the 'process_initializer' function was located in
	# 'celery.worker'. In Celery 2.5 the function 'process_initializer'
	# was moved to the module 'celery.concurrency.processes'.

        _process_initializer = module.process_initializer

        @functools.wraps(module.process_initializer)
        def process_initializer(*args, **kwargs):
            application_instance().activate()
            return _process_initializer(*args, **kwargs)

        module.process_initializer = process_initializer

def instrument_celery_loaders_base(module):

    def force_application_activation(*args, **kwargs):
        application_instance().activate()

    wrap_pre_function(module, 'BaseLoader.init_worker',
            force_application_activation)
