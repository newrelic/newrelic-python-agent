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

import functools

import newrelic.packages.asgiref_compatibility as asgiref_compatibility
from newrelic.api.application import application_instance
from newrelic.api.web_transaction import WebTransaction
from newrelic.common.object_names import callable_name
from newrelic.common.object_wrapper import wrap_object
from newrelic.common.async_proxy import CoroutineProxy, LoopContext


class ASGIWebTransaction(WebTransaction):
    def __init__(self, application, scope, receive, send):
        self.receive = receive
        self._send = send
        scheme = scope.get("scheme", "http")
        if "server" in scope:
            host, port = scope["server"] = tuple(scope["server"])
        else:
            host, port = None, None
        request_method = scope["method"]
        request_path = scope["path"]
        query_string = scope["query_string"]
        headers = scope["headers"] = tuple(scope["headers"])
        super(ASGIWebTransaction, self).__init__(
            application=application,
            name=None,
            scheme=scheme,
            host=host,
            port=port,
            request_method=request_method,
            request_path=request_path,
            query_string=query_string,
            headers=headers,
        )

    async def send(self, event):
        if event["type"] == "http.response.start":
            self.process_response(event["status"], event.get("headers", ()))
        return await self._send(event)


def make_single_callable(original, wrapped, application, name, group, framework):
    async def nr_asgi_wrapper(scope, receive, send):
        if scope["type"] != "http":
            return await wrapped(scope, receive, send)

        _application = application_instance(application)

        with ASGIWebTransaction(
            application=_application, scope=scope, receive=receive, send=send
        ) as transaction:

            # Override the initial web transaction name to be the supplied
            # name, or the name of the wrapped callable if wanting to use
            # the callable as the default. This will override the use of a
            # raw URL which can result in metric grouping issues where a
            # framework is not instrumented or is leaking URLs.
            #
            # Note that at present if default for naming scheme is still
            # None and we aren't specifically wrapping a designated
            # framework, then we still allow old URL based naming to
            # override. When we switch to always forcing a name we need to
            # check for naming scheme being None here.

            settings = transaction._settings

            if name is None and settings:
                naming_scheme = settings.transaction_name.naming_scheme

                if framework is not None:
                    if naming_scheme in (None, "framework"):
                        transaction.set_transaction_name(
                            callable_name(original), priority=1
                        )

                elif naming_scheme in ("component", "framework"):
                    transaction.set_transaction_name(
                        callable_name(original), priority=1
                    )

            elif name:
                transaction.set_transaction_name(name, group, priority=1)

            coro = wrapped(scope, transaction.receive, transaction.send)
            coro = CoroutineProxy(coro, LoopContext())
            return await coro

    return nr_asgi_wrapper


def make_double_callable(wrapped, *args, **kwargs):
    class NRAsgiWrapper(object):
        def __init__(self, scope):
            self.scope = scope
            _wrapped = asgiref_compatibility.double_to_single_callable(wrapped)
            self.wrapped = make_single_callable(wrapped, _wrapped, *args, **kwargs)

        async def __call__(self, receive, send):
            return await self.wrapped(self.scope, receive, send)

    return NRAsgiWrapper


def ASGIApplicationWrapper(
    wrapped, application=None, name=None, group=None, framework=None
):

    if asgiref_compatibility.is_double_callable(wrapped):
        return make_double_callable(wrapped, application, name, group, framework)
    else:
        return make_single_callable(
            wrapped, wrapped, application, name, group, framework
        )


def asgi_application(application=None, name=None, group=None, framework=None):
    return functools.partial(
        ASGIApplicationWrapper,
        application=application,
        name=name,
        group=group,
        framework=framework,
    )


def wrap_asgi_application(
    module, object_path, application=None, name=None, group=None, framework=None
):
    wrap_object(
        module,
        object_path,
        ASGIApplicationWrapper,
        (application, name, group, framework),
    )
