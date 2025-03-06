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

"""This module provides instrumentation for Celery.

Note that Celery has a habit of moving things around in code base or of
completely rewriting stuff across minor versions. See additional notes
about this below.

"""

import functools

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.message_trace import MessageTrace
from newrelic.api.pre_function import wrap_pre_function
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import FunctionWrapper, _NRBoundFunctionWrapper, wrap_function_wrapper
from newrelic.core.agent import shutdown_agent

UNKNOWN_TASK_NAME = "<Unknown Task>"
MAPPING_TASK_NAMES = {"celery.starmap", "celery.map"}


def task_info(instance, *args, **kwargs):
    # Grab the current task, which can be located in either place
    if instance:
        task = instance
    elif args:
        task = args[0]
    elif "task" in kwargs:
        task = kwargs["task"]
    else:
        return UNKNOWN_TASK_NAME  # Failsafe

    # Task can be either a task instance or a signature, which subclasses dict, or an actual dict in some cases.
    task_name = getattr(task, "name", None) or task.get("task", UNKNOWN_TASK_NAME)
    task_source = task

    # Under mapping tasks, the root task name isn't descriptive enough so we append the
    # subtask name to differentiate between different mapping tasks
    if task_name in MAPPING_TASK_NAMES:
        try:
            subtask = kwargs["task"]["task"]
            task_name = f"{task_name}/{subtask}"
            task_source = task.app._tasks[subtask]
        except Exception:
            pass

    return task_name, task_source


def CeleryTaskWrapper(wrapped):
    def wrapper(wrapped, instance, args, kwargs):
        transaction = current_transaction(active_only=False)

        # Grab task name and source
        _name, _source = task_info(instance, *args, **kwargs)

        # A Celery Task can be called either outside of a transaction, or
        # within the context of an existing transaction. There are 3
        # possibilities we need to handle:
        #
        #   1. In an inactive transaction
        #
        #      If the end_of_transaction() or ignore_transaction() API calls
        #      have been invoked, this task may be called in the context
        #      of an inactive transaction. In this case, don't wrap the task
        #      in any way. Just run the original function.
        #
        #   2. In an active transaction
        #
        #      Run the original function inside a FunctionTrace.
        #
        #   3. Outside of a transaction
        #
        #      This is the typical case for a celery Task. Since it's not
        #      running inside of an existing transaction, we want to create
        #      a new background transaction for it.

        if transaction and (transaction.ignore_transaction or transaction.stopped):
            return wrapped(*args, **kwargs)

        elif transaction:
            with FunctionTrace(_name, source=_source):
                return wrapped(*args, **kwargs)

        else:
            with BackgroundTask(application_instance(), _name, "Celery", source=_source) as transaction:
                # Attempt to grab distributed tracing headers
                try:
                    # Headers on earlier versions of Celery may end up as attributes
                    # on the request context instead of as custom headers. Handler this
                    # by defaulting to using vars() if headers is not available
                    request = instance.request
                    headers = getattr(request, "headers", None) or vars(request)

                    settings = transaction.settings
                    if headers is not None and settings is not None:
                        if settings.distributed_tracing.enabled:
                            transaction.accept_distributed_trace_headers(headers, transport_type="AMQP")
                        elif transaction.settings.cross_application_tracer.enabled:
                            transaction._process_incoming_cat_headers(
                                headers.get(MessageTrace.cat_id_key, None),
                                headers.get(MessageTrace.cat_transaction_key, None),
                            )
                except Exception:
                    pass

                return wrapped(*args, **kwargs)

    # Celery tasks that inherit from celery.app.task must implement a run()
    # method.
    # ref: (http://docs.celeryproject.org/en/2.5/reference/
    #                            celery.app.task.html#celery.app.task.BaseTask)
    # Celery task's __call__ method then calls the run() method to execute the
    # task. But celery does a micro-optimization where if the __call__ method
    # was not overridden by an inherited task, then it will directly execute
    # the run() method without going through the __call__ method. Our
    # instrumentation via FunctionWrapper() relies on __call__ being called which
    # in turn executes the wrapper() function defined above. Since the micro
    # optimization bypasses __call__ method it breaks our instrumentation of
    # celery.
    #
    # For versions of celery 2.5.3 to 2.5.5+
    # Celery has included a monkey-patching provision which did not perform this
    # optimization on functions that were monkey-patched. Unfortunately, our
    # wrappers are too transparent for celery to detect that they've even been
    # monky-patched. To circumvent this, we set the __module__ of our wrapped task
    # to this file which causes celery to properly detect that it has been patched.
    #
    # For versions of celery 2.5.3 to 2.5.5
    # To circumvent this problem, we added a run() attribute to our
    # FunctionWrapper which points to our __call__ method. This causes Celery
    # to execute our __call__ method which in turn applies the wrapper
    # correctly before executing the task.

    class TaskWrapper(FunctionWrapper):
        def run(self, *args, **kwargs):
            return self.__call__(*args, **kwargs)

    wrapped_task = TaskWrapper(wrapped, wrapper)
    # Reset __module__ to be less transparent so celery detects our monkey-patching
    wrapped_task.__module__ = CeleryTaskWrapper.__module__

    return wrapped_task


def instrument_celery_app_task(module):
    # Triggered for both 'celery.app.task' and 'celery.task.base'.

    if hasattr(module, "BaseTask"):
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

        if module.BaseTask.__module__ == module.__name__:
            module.BaseTask.__call__ = CeleryTaskWrapper(module.BaseTask.__call__)


def wrap_Celery_send_task(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    # Merge distributed tracing headers into outgoing task headers
    try:
        dt_headers = MessageTrace.generate_request_headers(transaction)
        original_headers = kwargs.get("headers", None)
        if dt_headers:
            if not original_headers:
                kwargs["headers"] = dict(dt_headers)
            else:
                kwargs["headers"] = dt_headers = dict(dt_headers)
                dt_headers.update(dict(original_headers))
    except Exception:
        pass

    return wrapped(*args, **kwargs)


def wrap_worker_optimizations(wrapped, instance, args, kwargs):
    # Attempt to uninstrument BaseTask before stack protection is installed or uninstalled
    try:
        from celery.app.task import BaseTask

        if isinstance(BaseTask.__call__, _NRBoundFunctionWrapper):
            BaseTask.__call__ = BaseTask.__call__.__wrapped__
    except Exception:
        BaseTask = None

    # Allow metaprogramming to run
    result = wrapped(*args, **kwargs)

    # Rewrap finalized BaseTask
    if BaseTask:  # Ensure imports succeeded
        BaseTask.__call__ = CeleryTaskWrapper(BaseTask.__call__)

    return result


def instrument_celery_app_base(module):
    if hasattr(module, "Celery") and hasattr(module.Celery, "send_task"):
        wrap_function_wrapper(module, "Celery.send_task", wrap_Celery_send_task)


def instrument_celery_worker(module):
    # Triggered for 'celery.worker' and 'celery.concurrency.processes'.

    if hasattr(module, "process_initializer"):
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

    wrap_pre_function(module, "BaseLoader.init_worker", force_application_activation)


def instrument_billiard_pool(module):
    def force_agent_shutdown(*args, **kwargs):
        shutdown_agent()

    if hasattr(module, "Worker"):
        wrap_pre_function(module, "Worker._do_exit", force_agent_shutdown)


def instrument_celery_app_trace(module):
    # Uses same wrapper for setup and reset worker optimizations to prevent patching and unpatching from removing wrappers
    if hasattr(module, "setup_worker_optimizations"):
        wrap_function_wrapper(module, "setup_worker_optimizations", wrap_worker_optimizations)

    if hasattr(module, "reset_worker_optimizations"):
        wrap_function_wrapper(module, "reset_worker_optimizations", wrap_worker_optimizations)
