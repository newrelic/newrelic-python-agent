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

import os
import re
import urllib.parse as urlparse

from newrelic.api.application import application_instance
from newrelic.api.transaction import current_transaction
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.common.signature import bind_args
from newrelic.common.utilization import AZURE_RESOURCE_GROUP_NAME_PARTIAL_RE, AZURE_RESOURCE_GROUP_NAME_RE


def original_agent_instance():
    app_name = os.environ.setdefault("NEW_RELIC_APP_NAME", os.getenv("WEBSITE_SITE_NAME", ""))

    return application_instance(app_name)


def intrinsics_populator(application, context):
    # For now, only HTTP triggers are supported
    trigger_type = "http"

    website_owner_name = os.environ.get("WEBSITE_OWNER_NAME", None)
    if not website_owner_name:
        subscription_id = "Unknown"
    else:
        subscription_id = re.search(r"(?:(?!\+).)*", website_owner_name) and re.search(
            r"(?:(?!\+).)*", website_owner_name
        ).group(0)
    if website_owner_name and website_owner_name.endswith("-Linux"):
        resource_group_name = AZURE_RESOURCE_GROUP_NAME_RE.search(website_owner_name).group(1)
    elif website_owner_name:
        resource_group_name = AZURE_RESOURCE_GROUP_NAME_PARTIAL_RE.search(website_owner_name).group(1)
    else:
        resource_group_name = os.environ.get("WEBSITE_RESOURCE_GROUP", "Unknown")
    azure_function_app_name = os.environ.get("WEBSITE_SITE_NAME", getattr(application, "name", "Azure Function App"))

    cloud_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{azure_function_app_name}/functions/{getattr(context, 'function_name', 'Unknown')}"
    faas_name = f"{azure_function_app_name}/{getattr(context, 'function_name', 'Unknown')}"

    return {
        "cloud.resource_id": cloud_resource_id,
        "faas.name": faas_name,
        "faas.trigger": trigger_type,
        "faas.invocation_id": getattr(context, "invocation_id", "Unknown"),
    }


# TODO: This should serve as a way to determine the trigger type.
# Right now, we only support HTTP, so this function serves to activate
# the application if not already registered with the collector as well
# as determining if this invocation was a cold start or not.
async def wrap_dispatcher__handle__invocation_request(wrapped, instance, args, kwargs):
    # Logic to determine if this is a cold start since we are not
    # able to access the logic in the __init__ method of the Dispatcher
    # class with Python (in the Portal, this is not done in Python)
    if not hasattr(instance, "_nr_running_dispatcher"):
        instance._nr_running_dispatcher = True
        instance._nr_cold_start = True

    bound_args = bind_args(wrapped, args, kwargs)

    request = bound_args.get("request", None)

    if not request:
        return await wrapped(*args, **kwargs)

    try:
        # Once other trigger types are supported, we need
        # to create attribute checks for this functionality:
        function_id = request.invocation_request.function_id
        binding_type = instance._functions.get_function(function_id).trigger_metadata["type"]

        # For now, NR only supports HTTP triggers.
        # In the future, we will have setup logic for other
        # trigger types within this instrumentation.
        if not binding_type.startswith("http"):
            return await wrapped(*args, **kwargs)

    except Exception:
        pass

    return await wrapped(*args, **kwargs)


async def wrap_dispatcher__run_async_func(wrapped, instance, args, kwargs):
    from azure.functions.http import HttpRequest

    bound_args = bind_args(wrapped, args, kwargs)

    context = bound_args.get("context", None)
    func = bound_args.get("func", None)
    params = bound_args.get("params", None)

    application = original_agent_instance()

    http_request = None
    for value in params.values():
        if isinstance(value, HttpRequest):
            http_request = value
            url_split = urlparse.urlsplit(getattr(http_request, "url", ":///?#"))
            scheme = getattr(url_split, "scheme", None)
            query = getattr(url_split, "query", None)
            host, port = (
                (getattr(url_split, "netloc", None), None)
                if (":" not in getattr(url_split, "netloc", None))
                else getattr(url_split, "netloc", None).split(":")
            )
            break

    # If this is an HTTP http_request object, create a web transaction.
    # Otherwise, create appropriate type of Transaction in the future
    if http_request:
        transaction = WebTransaction(
            application=application,
            name=getattr(context, "function_name", "azure_function"),
            group="AzureFunction",
            scheme=scheme,
            host=host,
            port=port,
            request_method=getattr(http_request, "method", None),
            request_path=getattr(http_request, "url", None),
            query_string=query,
            headers=dict(http_request.headers),
            source=func,
        )

        if not transaction:
            return await wrapped(*args, **kwargs)

        if hasattr(instance, "_nr_cold_start"):
            cold_start = True
            # Delete the attribute so that subsequent calls to this
            # method are noted as not being cold starts
            del instance._nr_cold_start
        else:
            cold_start = False

        azure_intrinsics = intrinsics_populator(application, context)

        # Only add this attribute if this is a cold start
        if cold_start:
            azure_intrinsics.update({"faas.coldStart": True})

        with transaction:
            for key, value in azure_intrinsics.items():
                transaction._add_agent_attribute(key, value)
            return await wrapped(*args, **kwargs)

    return await wrapped(*args, **kwargs)


def wrap_dispatcher__run_sync_func(wrapped, instance, args, kwargs):
    from azure.functions.http import HttpRequest

    bound_args = bind_args(wrapped, args, kwargs)

    context = bound_args.get("context", None)
    func = bound_args.get("func", None)
    params = bound_args.get("params", None)

    application = original_agent_instance()

    http_request = None
    for value in params.values():
        if isinstance(value, HttpRequest):
            http_request = value
            url_split = urlparse.urlsplit(getattr(http_request, "url", ":///?#"))
            scheme = getattr(url_split, "scheme", None)
            query = getattr(url_split, "query", None)
            host, port = (
                (getattr(url_split, "netloc", None), None)
                if (":" not in getattr(url_split, "netloc", None))
                else getattr(url_split, "netloc", None).split(":")
            )
            break

    # If this is an HTTP Request object, we can create a web transaction
    if http_request:
        transaction = WebTransaction(
            application=application,
            name=getattr(context, "function_name", "azure_function"),
            group="AzureFunction",
            scheme=scheme,
            host=host,
            port=port,
            request_method=getattr(http_request, "method", None),
            request_path=getattr(http_request, "url", None),
            query_string=query,
            headers=dict(http_request.headers),
            source=func,
        )

        if not transaction:
            return wrapped(*args, **kwargs)

        if hasattr(instance, "_nr_cold_start"):
            cold_start = True
            # Delete the attribute so that subsequent calls to this
            # method are noted as not being cold starts
            del instance._nr_cold_start
        else:
            cold_start = False

        azure_intrinsics = intrinsics_populator(application, context)

        # Only add this attribute if this is a cold start
        if cold_start:
            azure_intrinsics.update({"faas.coldStart": True})

        with transaction:
            for key, value in azure_intrinsics.items():
                transaction._add_agent_attribute(key, value)
            return wrapped(*args, **kwargs)

    return wrapped(*args, **kwargs)


def wrap_httpresponse__init__(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    bound_args = bind_args(wrapped, args, kwargs)

    status_code = bound_args.get("status_code", None)
    headers = bound_args.get("headers", None)

    if status_code:
        transaction.process_response(status_code, headers)

    return wrapped(*args, **kwargs)


def instrument_azure_function__http(module):
    if hasattr(module, "HttpResponse"):
        wrap_function_wrapper(module, "HttpResponse.__init__", wrap_httpresponse__init__)


def instrument_azure_functions_worker_dispatcher(module):
    if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_handle__invocation_request"):
        wrap_function_wrapper(
            module, "Dispatcher._handle__invocation_request", wrap_dispatcher__handle__invocation_request
        )
    if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_run_sync_func"):
        wrap_function_wrapper(module, "Dispatcher._run_sync_func", wrap_dispatcher__run_sync_func)
    if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_run_async_func"):
        wrap_function_wrapper(module, "Dispatcher._run_async_func", wrap_dispatcher__run_async_func)
