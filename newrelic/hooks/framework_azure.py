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


# TODO: This should serve as a way to determine the trigger type.
# Right now, we only support HTTP, so this function serves to activate
# the application if not already registered with the collector as well
# as determining if this invocation was a cold start or not.
async def wrap_dispatcher__handle__invocation_request(wrapped, instance, args, kwargs):
    def bind_params(request, *args, **kwargs):
        return request

    # Force default registration of the application instance
    # instead of lazy registration upon the first request
    app_name = os.environ.get("NEW_RELIC_APP_NAME", os.environ.get("WEBSITE_SITE_NAME", None))
    application = application_instance(app_name, activate=False)
    if application and not application.active:
        application.activate()
    elif not application:
        application = application_instance(app_name)
        application.activate()

    # Logic to determine if this is a cold start since we are not
    # able to access the logic in the __init__ method of the Dispatcher
    # class with Python (in the Portal, this is done in C#)
    if not hasattr(instance, "_nr_running_dispatcher"):
        instance._nr_running_dispatcher = True
        instance._nr_cold_start = True

    request = bind_params(*args, **kwargs)

    if not request:
        return await wrapped(*args, **kwargs)

    # For now, NR only supports HTTP triggers
    function_id = request.invocation_request.function_id

    binding_type = instance._functions.get_function(function_id).trigger_metadata["type"]
    if not binding_type.startswith("http"):
        return await wrapped(*args, **kwargs)

    return await wrapped(*args, **kwargs)


async def wrap_dispatcher__run_async_func(wrapped, instance, args, kwargs):
    from azure.functions.http import HttpRequest

    def bind_params(context, func, args, *_args, **_kwargs):
        return context, func, args

    context, func, params = bind_params(*args, **kwargs)

    application = application_instance(
        os.environ.get("NEW_RELIC_APP_NAME", os.environ.get("WEBSITE_SITE_NAME", None)), activate=False
    )
    if application and not application.active:
        application.activate()
    elif not application:
        application = application_instance(
            os.environ.get("NEW_RELIC_APP_NAME", os.environ.get("WEBSITE_SITE_NAME", None))
        )
        application.activate()

    http_request = None
    for key, value in params.items():
        if isinstance(value, HttpRequest):
            http_request = value
            url_split = urlparse.urlsplit(http_request.url)
            scheme = url_split.scheme
            query = url_split.query
            host, port = url_split.netloc, None if (":" not in url_split.netloc) else url_split.netloc.split(":")
            break

    # If this is an HTTP http_request object, create a web transaction.
    # Otherwise, create appropriate type of Transaction in the future
    if http_request:
        transaction = WebTransaction(
            application=application,
            name=context.function_name,
            group="AzureFunction",
            scheme=scheme,
            host=host,
            port=port,
            request_method=http_request.method,
            request_path=http_request.url,
            query_string=query,
            headers=dict(http_request.headers),
            source=func,
        )

        # For now, only HTTP triggers are supported
        trigger_type = "http"

        if hasattr(instance, "_nr_cold_start"):
            cold_start = True
            # Delete the attribute so that subsequent calls to this
            # method are noted as not being cold starts
            del instance._nr_cold_start
        else:
            cold_start = False

        website_owner_name = os.environ.get("WEBSITE_OWNER_NAME", None)
        subscription_id = re.search(r"(?:(?!\+).)*", website_owner_name) and re.search(
            r"(?:(?!\+).)*", website_owner_name
        ).group(1)
        resource_group_name = os.environ.get(
            "WEBSITE_RESOURCE_GROUP",
            None,
        )
        if resource_group_name is None:
            if website_owner_name.endswith("-Linux"):
                resource_group_name = re.search(r"\+([a-zA-z0-9\-]+)-[a-zA-Z0-9]+(?:-Linux)", website_owner_name).group(
                    1
                )
            else:
                resource_group_name = re.search(r"\+([a-zA-z0-9\-]+)-[a-zA-Z0-9]+", website_owner_name).group(1)
        azure_function_app_name = os.environ.get("WEBSITE_SITE_NAME", application.name)

        cloud_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{azure_function_app_name}/functions/{context.function_name}"
        faas_name = f"{azure_function_app_name}/{context.function_name}"

        azure_intrinsics = {
            "cloud.resource_id": cloud_resource_id,
            "faas.name": faas_name,
            "faas.trigger": trigger_type,
            "faas.invocation_id": context.invocation_id,
        }

        # Only add this attribute if this is a cold start
        if cold_start:
            azure_intrinsics.update({"faas.coldStart": True})

        if not transaction:
            return await wrapped(*args, **kwargs)

        with transaction:
            for key, value in azure_intrinsics.items():
                transaction._add_agent_attribute(key, value)
            response = await wrapped(*args, **kwargs)
            return response

    return await wrapped(*args, **kwargs)


def wrap_dispatcher__run_sync_func(wrapped, instance, args, kwargs):
    from azure.functions.http import HttpRequest

    def bind_params(invocation_id, context, func, params, *args, **kwargs):
        return invocation_id, context, func, params

    invocation_id, context, func, params = bind_params(*args, **kwargs)
    application = application_instance(
        os.environ.get("NEW_RELIC_APP_NAME", os.environ.get("WEBSITE_SITE_NAME", None)), activate=False
    )
    if application and not application.active:
        application.activate()
    elif not application:
        application = application_instance(
            os.environ.get("NEW_RELIC_APP_NAME", os.environ.get("WEBSITE_SITE_NAME", None))
        )
        application.activate()

    http_request = None
    for key, value in params.items():
        if isinstance(value, HttpRequest):
            http_request = value
            url_split = urlparse.urlsplit(http_request.url)
            scheme = url_split.scheme
            query = url_split.query
            host, port = url_split.netloc, None if (":" not in url_split.netloc) else url_split.netloc.split(":")
            break

    # If this is an HTTP Request object, we can create a web transaction
    if http_request:
        transaction = WebTransaction(
            application=application,
            name=context.function_name,
            group="AzureFunction",
            scheme=scheme,
            host=host,
            port=port,
            request_method=http_request.method,
            request_path=http_request.url,
            query_string=query,
            headers=dict(http_request.headers),
            source=func,
        )

        # For now, only HTTP triggers are supported
        trigger_type = "http"

        if hasattr(instance, "_nr_cold_start"):
            cold_start = True
            # Delete the attribute so that subsequent calls to this
            # method are noted as not being cold starts
            del instance._nr_cold_start
        else:
            cold_start = False

        website_owner_name = os.environ.get("WEBSITE_OWNER_NAME", None)
        subscription_id = re.search(r"(?:(?!\+).)*", website_owner_name) and re.search(
            r"(?:(?!\+).)*", website_owner_name
        ).group(1)
        resource_group_name = os.environ.get(
            "WEBSITE_RESOURCE_GROUP",
            None,
        )
        if resource_group_name is None:
            if website_owner_name.endswith("-Linux"):
                resource_group_name = re.search(r"\+([a-zA-z0-9\-]+)-[a-zA-Z0-9]+(?:-Linux)", website_owner_name).group(
                    1
                )
            else:
                resource_group_name = re.search(r"\+([a-zA-z0-9\-]+)-[a-zA-Z0-9]+", website_owner_name).group(1)
        azure_function_app_name = os.environ.get("WEBSITE_SITE_NAME", application.name)

        cloud_resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Web/sites/{azure_function_app_name}/functions/{context.function_name}"
        faas_name = f"{azure_function_app_name}/{context.function_name}"

        azure_intrinsics = {
            "cloud.resource_id": cloud_resource_id,
            "faas.name": faas_name,
            "faas.trigger": trigger_type,
            "faas.invocation_id": invocation_id,
        }

        # Only add this attribute if this is a cold start
        if cold_start:
            azure_intrinsics.update({"faas.coldStart": True})

        if not transaction:
            return wrapped(*args, **kwargs)

        with transaction:
            for key, value in azure_intrinsics.items():
                transaction._add_agent_attribute(key, value)
            response = wrapped(*args, **kwargs)
            return response

    return wrapped(*args, **kwargs)


def wrap_httpresponse__init__(wrapped, instance, args, kwargs):
    def bind_params(body=b"", status_code=None, headers=None, *args, **kwargs):
        return status_code, headers

    transaction = current_transaction()
    if not transaction:
        return wrapped(*args, **kwargs)

    status_code, headers = bind_params(*args, **kwargs)

    if status_code:
        transaction.process_response(status_code, headers)

    return wrapped(*args, **kwargs)


# def wrap_dispatcher_get_worker_metadata(wrapped, instance, args, kwargs):
#     breakpoint()
#     print("MADE IT TO get_worker_metadata")
#     return wrapped(*args, **kwargs)


def instrument_azure__http(module):
    if hasattr(module, "HttpResponse"):
        wrap_function_wrapper(module, "HttpResponse.__init__", wrap_httpresponse__init__)


def instrument_azure_functions_worker_dispatcher(module):
    # wrap_function_wrapper(module, "Dispatcher.__init__", wrap_dispatcher__init__)

    if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_handle__invocation_request"):
        wrap_function_wrapper(
            module, "Dispatcher._handle__invocation_request", wrap_dispatcher__handle__invocation_request
        )
    if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_run_sync_func"):
        wrap_function_wrapper(module, "Dispatcher._run_sync_func", wrap_dispatcher__run_sync_func)
    if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_run_async_func"):
        wrap_function_wrapper(module, "Dispatcher._run_async_func", wrap_dispatcher__run_async_func)

    # if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "get_worker_metadata"):
    #     wrap_function_wrapper(module, "Dispatcher.get_worker_metadata", wrap_dispatcher_get_worker_metadata)

    # if hasattr(module.Dispatcher, "connect"):
    #     wrap_function_wrapper(module, "Dispatcher.connect", wrap_dispatcher_connect)

    # if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_run_sync_func"):
    #     wrap_function_wrapper(module, "Dispatcher._run_sync_func", wrap_dispatcher__run_sync_func)
    # if hasattr(module, "Dispatcher") and hasattr(module.Dispatcher, "_run_async_func"):
    #     wrap_function_wrapper(module, "Dispatcher._run_async_func", wrap_dispatcher__run_async_func)
