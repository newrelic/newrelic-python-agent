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


import logging

from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.transaction import current_transaction, add_custom_attribute
from newrelic.api.time_trace import add_custom_span_attribute
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace

_logger = logging.getLogger(__name__)

CLIENT_ATTRIBUTES_WARNING_LOG_MSG = "Exception occurred in PyZeebe instrumentation: Failed to add client attributes."


# Adds client method params as txn or span attributes
def _add_client_input_attributes(method_name, txn, args, kwargs):
    try:
        if method_name in ("run_process", "run_process_with_result"):
            bpmn_id = kwargs.get("bpmn_process_id", args[0] if args else None)
            if bpmn_id:
                txn._add_agent_attribute("zeebe.client.bpmnProcessId", bpmn_id)
                # add_attr("zeebe.client.bpmnProcessId", bpmn_id)
        elif method_name == "publish_message":
            msg_name = kwargs.get("name", args[0] if args else None)
            if msg_name:
                txn._add_agent_attribute("zeebe.client.messageName", msg_name)
                # add_attr("zeebe.client.messageName", msg_name)
            correlation_key = kwargs.get("correlation_key", args[1] if args and len(args) > 1 else None)
            if correlation_key:
                txn._add_agent_attribute("zeebe.client.correlationKey", correlation_key)
                # add_attr("zeebe.client.correlationKey", correlation_key)
            message_id = kwargs.get("message_id")
            if message_id and len(args) > 4:
                message_id = args[4]
            if message_id:
                txn._add_agent_attribute("zeebe.client.messageId", message_id)
                # add_attr("zeebe.client.messageId", message_id)
        elif method_name == "deploy_resource":
            resources = list(args)
            if len(resources) == 1 and isinstance(resources[0], (list, tuple)):
                resources = list(resources[0])
            if resources:
                txn._add_agent_attribute("zeebe.client.resourceCount", len(resources))
                # add_attr("zeebe.client.resourceCount", len(resources))
                if len(resources) == 1:
                    try:
                        txn._add_agent_attribute("zeebe.client.resourceFile", str(resources[0]))
                        # add_attr("zeebe.client.resourceFile", str(resources[0]))
                    except Exception:
                        txn._add_agent_attribute("zeebe.client.resourceFile", str(resources[0]))
                        # add_attr("zeebe.client.resourceFile", repr(resources[0]))
    except Exception:
        _logger.warning(CLIENT_ATTRIBUTES_WARNING_LOG_MSG, exc_info=True)


# Async wrapper that instruments router/worker annotations`
async def _nr_wrapper_execute_one_job(wrapped, instance, args, kwargs):
    job = args[0] if args else kwargs.get("job")
    process_id = getattr(job, "bpmn_process_id", None) or "UnknownProcess"
    task_type = getattr(job, "type", None) or "UnknownType"
    txn_name = f"{process_id}/{task_type}"

    with BackgroundTask(application_instance(), txn_name, group="ZeebeTask"):
        if job is not None:
            if hasattr(job, "key"):
                add_custom_attribute("zeebe.job.key", job.key)
            if hasattr(job, "type"):
                add_custom_attribute("zeebe.job.type", job.type)
            if hasattr(job, "bpmn_process_id"):
                add_custom_attribute("zeebe.job.bpmnProcessId", job.bpmn_process_id)
            if hasattr(job, "process_instance_key"):
                add_custom_attribute("zeebe.job.processInstanceKey", job.process_instance_key)
            if hasattr(job, "element_id"):
                add_custom_attribute("zeebe.job.elementId", job.element_id)

        result = await wrapped(*args, **kwargs)
        return result


# Async wrapper that instruments a ZeebeClient method.
def _nr_client_wrapper(method_name):
    async def wrapper(wrapped, instance, args, kwargs):
        txn = current_transaction()
        if txn:
            # add_fn = add_custom_span_attribute
            _add_client_input_attributes(method_name, txn, args, kwargs)
            with FunctionTrace(name=method_name, group="ZeebeClient"):
                result = await wrapped(*args, **kwargs)
            return result
        else:
            # add_fn = add_custom_attribute
            created_txn = BackgroundTask(application=application_instance(), name=method_name, group="ZeebeClient")
            created_txn.__enter__()
            _add_client_input_attributes(method_name, created_txn, args, kwargs)
            try:
                result = await wrapped(*args, **kwargs)
            finally:
                created_txn.__exit__(None, None, None)

            return result

    return wrapper


# Instrument JobExecutor.execute_one_job to create a background transaction per job (invoked from @router.task or @worker.task annotations)
def instrument_pyzeebe_worker_job_executor(module):
    if hasattr(module, "JobExecutor"):
        wrap_function_wrapper(module, "JobExecutor.execute_one_job", _nr_wrapper_execute_one_job)


# Instrument ZeebeClient methods to trace client calls.
def instrument_pyzeebe_client_client(module):
    target_methods = ("run_process", "run_process_with_result", "deploy_resource", "publish_message")

    for method_name in target_methods:
        if hasattr(module, "ZeebeClient"):
            if hasattr(module.ZeebeClient, method_name):
                wrap_function_wrapper(module, f"ZeebeClient.{method_name}", _nr_client_wrapper(method_name))
