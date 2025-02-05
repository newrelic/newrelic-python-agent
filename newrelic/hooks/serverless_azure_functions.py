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

# from inspect import isclass

from newrelic.api.asgi_application import ASGIApplicationWrapper

# from newrelic.api.time_trace import notice_error
# from newrelic.api.transaction import current_transaction
from newrelic.api.wsgi_application import (
    WSGIApplicationWrapper,  # , wrap_wsgi_application
)

# from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_function_wrapper  # , function_wrapper
from newrelic.common.package_version_utils import get_package_version

# from newrelic.api.function_trace import FunctionTrace, FunctionTraceWrapper, wrap_function_trace


AZURE_VERSION = ("Azure", get_package_version("azure-functions"))


def wrap_WsgiFunctionApp_app_object(wrapped, instance, args, kwargs):
    # Make sure that this works after going through WsgiMiddleware class
    def bind__init__(app, *args, **kwargs):
        return app, args, kwargs

    wsgi_app, args, kwargs = bind__init__(*args, **kwargs)

    wsgi_app = WSGIApplicationWrapper(wsgi_app, dispatcher=AZURE_VERSION)

    return wrapped(wsgi_app, *args, **kwargs)


def wrap_AsgiFunctionApp_app_object(wrapped, instance, args, kwargs):
    # Make sure that this works after going through WsgiMiddleware class
    def bind__init__(app, *args, **kwargs):
        return app, args, kwargs

    wsgi_app, args, kwargs = bind__init__(*args, **kwargs)

    wsgi_app = ASGIApplicationWrapper(wsgi_app, dispatcher=AZURE_VERSION)

    return wrapped(wsgi_app, *args, **kwargs)


def instrument_azure_functions(module):
    wrap_function_wrapper(module, "WsgiFunctionApp.__init__", wrap_WsgiFunctionApp_app_object)
    wrap_function_wrapper(module, "AsgiFunctionApp.__init__", wrap_AsgiFunctionApp_app_object)

    # wrap_wsgi_application(module, "WsgiFunctionApp.__init__", framework=AZURE_VERSION)

    # AI generated...maybe:
    # wrap_function_wrapper(module, "_http.HttpRequest.__init__", _nr_wrapper_azure_functions_HttpRequest___init_)
    # wrap_function_wrapper(module, "_http.HttpResponse.__init__", _nr_wrapper_azure_functions_HttpResponse___init_)


# def instrument_flask_app(module):
#     wrap_wsgi_application(module, "Flask.wsgi_app", framework=FLASK_VERSION)

#     wrap_function_wrapper(module, "Flask.add_url_rule", _nr_wrapper_Flask_add_url_rule_input_)

#     if hasattr(module.Flask, "endpoint"):
#         wrap_function_wrapper(module, "Flask.endpoint", _nr_wrapper_Flask_endpoint_)
