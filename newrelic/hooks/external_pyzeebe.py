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
from newrelic.api.web_transaction import WebTransaction
from newrelic.api.function_trace import FunctionTrace
from newrelic.api.transaction import current_transaction
from newrelic.common.object_wrapper import wrap_function_wrapper

_logger = logging.getLogger(__name__)

CLIENT_ATTRIBUTES_DEPLOY_RESOURCE_LOG_MSG = "Exception occurred in PyZeebe instrumentation: Failed to extract resource count/file for method `deploy_resource`. Report this issue to New Relic support."


# Adds client method params as txn or span attributes
def _add_client_input_attributes(method_name, trace, args, kwargs):
    bpmn_id = extract_agent_attribute_from_methods(args, kwargs, method_name, ("run_process", "run_process_with_result"), "bpmn_process_id", 0)
    if bpmn_id:
        trace._add_agent_attribute("zeebe.client.bpmnProcessId", bpmn_id)

    msg_name = extract_agent_attribute_from_methods(args, kwargs, method_name, ("publish_message"), "name", 0)
    if msg_name:
        trace._add_agent_attribute("zeebe.client.messageName", msg_name)

    correlation_key = extract_agent_attribute_from_methods(args, kwargs, method_name, ("publish_message"), "correlation_key", 1)
    if correlation_key:
        trace._add_agent_attribute("zeebe.client.correlationKey", correlation_key)
    
    message_id = extract_agent_attribute_from_methods(args, kwargs, method_name, ("publish_message"), "message_id", 4)
    if message_id:
        trace._add_agent_attribute("zeebe.client.messageId", message_id)
    
    resource = extract_agent_attribute_from_methods(args, {}, method_name, ("deploy_resource"), None, 0)
    if resource:
        try:
            trace._add_agent_attribute("zeebe.client.resourceFile", resource)
        except Exception:
            _logger.warning(CLIENT_ATTRIBUTES_DEPLOY_RESOURCE_LOG_MSG, exc_info=True)


def extract_agent_attribute_from_methods(args, kwargs, method_name, methods, param, index):
    try:
        if method_name in methods:
            value = kwargs.get(param)
            if not value and args and len(args) > index:
                value = args[index]
            return value
    except Exception:
        _logger.warning(f"Exception occurred in PyZeebe instrumentation: failed to extract {param} from {method_name}. Report this issue to New Relic support.", exc_info=True)

# Async wrapper that instruments router/worker annotations`
async def _nr_wrapper_execute_one_job(wrapped, instance, args, kwargs):
    job = args[0] if args else kwargs.get("job")
    process_id = getattr(job, "bpmn_process_id", None) or "UnknownProcess"
    task_type = getattr(job, "type", None) or "UnknownType"
    txn_name = f"{process_id}/{task_type}"

    with WebTransaction(application_instance(), txn_name, group="ZeebeTask") as txn:
        if job is not None:
            if hasattr(job, "key"):
                txn.add_custom_attribute("zeebe.job.key", job.key)
            if hasattr(job, "type"):
                txn.add_custom_attribute("zeebe.job.type", job.type)
            if hasattr(job, "bpmn_process_id"):
                txn.add_custom_attribute("zeebe.job.bpmnProcessId", job.bpmn_process_id)
            if hasattr(job, "process_instance_key"):
                txn.add_custom_attribute("zeebe.job.processInstanceKey", job.process_instance_key)
            if hasattr(job, "element_id"):
                txn.add_custom_attribute("zeebe.job.elementId", job.element_id)

        return await wrapped(*args, **kwargs)


# Async wrapper that instruments a ZeebeClient method.
def _nr_client_wrapper(method_name):
    async def _client_wrapper(wrapped, instance, args, kwargs):
        txn = current_transaction()
        if not txn:
            return await wrapped(*args, **kwargs)

        with FunctionTrace(name=method_name, group="ZeebeClient") as trace:
            _add_client_input_attributes(method_name, trace, args, kwargs)
            return await wrapped(*args, **kwargs)

    return _client_wrapper


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
