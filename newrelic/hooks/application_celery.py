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
from newrelic.common.object_wrapper import FunctionWrapper, wrap_function_wrapper
from newrelic.common.signature import bind_args
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


def wrap_task_call(wrapped, instance, args, kwargs):
    transaction = current_transaction(active_only=False)

    # Grab task name and source
    _name, _source = task_info(wrapped, *args, **kwargs)

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
                request = wrapped.request
                headers = getattr(request, "headers", None) or vars(request)

                settings = transaction.settings
                if headers is not None and settings is not None:
                    if settings.distributed_tracing.enabled:
                        if not transaction.accept_distributed_trace_headers(headers, transport_type="AMQP"):
                            try:
                                dt_headers = MessageTrace.generate_request_headers(transaction)
                                if dt_headers:
                                    if not headers:
                                        wrapped.request.headers = dict(dt_headers)
                                    else:
                                        headers.update(dict(dt_headers))
                                        wrapped.request.headers = headers
                            except Exception:
                                pass
                    elif transaction.settings.cross_application_tracer.enabled:
                        transaction._process_incoming_cat_headers(
                            headers.get(MessageTrace.cat_id_key, None),
                            headers.get(MessageTrace.cat_transaction_key, None),
                        )
            except Exception:
                pass

            return wrapped(*args, **kwargs)


def wrap_build_tracer(wrapped, instance, args, kwargs):
    class TaskWrapper(FunctionWrapper):
        def run(self, *args, **kwargs):
            return self.__call__(*args, **kwargs)

    try:
        bound_args = bind_args(wrapped, args, kwargs)
        task = bound_args.get("task", None)

        task = TaskWrapper(task, wrap_task_call)
        task.__module__ = wrapped.__module__  # Ensure module is set for monkeypatching detection
        bound_args["task"] = task

        return wrapped(**bound_args)
    except:
        # If we can't bind the args, we just call the wrapped function
        return wrapped(*args, **kwargs)


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
                            if not transaction.accept_distributed_trace_headers(headers, transport_type="AMQP"):
                                try:
                                    dt_headers = MessageTrace.generate_request_headers(transaction)
                                    if dt_headers:
                                        if not headers:
                                            instance.request.headers = dict(dt_headers)
                                        else:
                                            headers.update(dict(dt_headers))
                                            instance.request.headers = headers
                                except Exception:
                                    pass
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


def instrument_celery_local(module):
    if hasattr(module, "Proxy"):
        # This is used in the case where the function is
        # called directly on the Proxy object (rather than
        # using "delay" or "apply_async")
        module.Proxy.__call__ = CeleryTaskWrapper(module.Proxy.__call__)


def instrument_celery_worker(module):
    if hasattr(module, "process_initializer"):
        # We try and force activation of the agent before
        # the worker process starts.
        _process_initializer = module.process_initializer

        @functools.wraps(module.process_initializer)
        def process_initializer(*args, **kwargs):
            application_instance().activate()
            return _process_initializer(*args, **kwargs)

        module.process_initializer = process_initializer

    if hasattr(module, "process_destructor"):
        # We try and force shutdown of the agent before
        # the worker process exits.
        _process_destructor = module.process_destructor

        @functools.wraps(module.process_destructor)
        def process_destructor(*args, **kwargs):
            shutdown_agent()
            return _process_destructor(*args, **kwargs)

        module.process_destructor = process_destructor


def instrument_celery_loaders_base(module):
    def force_application_activation(*args, **kwargs):
        application_instance().activate()

    wrap_pre_function(module, "BaseLoader.init_worker", force_application_activation)


def instrument_billiard_pool(module):
    def force_agent_shutdown(*args, **kwargs):
        shutdown_agent()

    if hasattr(module, "Worker") and hasattr(module.Worker, "_do_exit"):
        wrap_pre_function(module, "Worker._do_exit", force_agent_shutdown)


def instrument_celery_app_trace(module):
    if hasattr(module, "build_tracer"):
        wrap_function_wrapper(module, "build_tracer", wrap_build_tracer)
