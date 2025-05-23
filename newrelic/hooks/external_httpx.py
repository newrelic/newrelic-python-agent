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

from newrelic.api.external_trace import ExternalTrace
from newrelic.common.object_wrapper import wrap_function_wrapper


def newrelic_event_hook(response):
    tracer = getattr(response.request, "_nr_trace", None)
    if tracer is not None:
        headers = dict(getattr(response, "headers", ())).items()
        tracer.process_response(getattr(response, "status_code", None), headers)


async def newrelic_event_hook_async(response):
    tracer = getattr(response.request, "_nr_trace", None)
    if tracer is not None:
        headers = dict(getattr(response, "headers", ())).items()
        tracer.process_response(getattr(response, "status_code", None), headers)


def newrelic_first_gen(wrapped, is_async=False):
    if is_async:
        yield newrelic_event_hook_async
    else:
        yield newrelic_event_hook
    while True:
        try:
            yield next(wrapped)
        except StopIteration:
            break


class NewRelicFirstList(list):
    def __init__(self, *args, is_async=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_async = is_async

    def __iter__(self):
        wrapped_iter = super().__iter__()
        return iter(newrelic_first_gen(wrapped_iter, self.is_async))


class NewRelicFirstDict(dict):
    def __init__(self, *args, is_async=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_async = is_async
        self.__setitem__("response", self["response"])

    def __setitem__(self, key, value):
        if key == "response":
            value = NewRelicFirstList(value, is_async=self.is_async)

        super().__setitem__(key, value)


def bind_request(request, *args, **kwargs):
    return request


def sync_send_wrapper(wrapped, instance, args, kwargs):
    request = bind_request(*args, **kwargs)

    with ExternalTrace("httpx", str(request.url), request.method, source=wrapped) as tracer:
        if hasattr(tracer, "generate_request_headers"):
            request._nr_trace = tracer
            outgoing_headers = tracer.generate_request_headers(tracer.transaction)
            for header_name, header_value in outgoing_headers:
                # User headers should override our CAT headers
                if header_name not in request.headers:
                    request.headers[header_name] = header_value

        return wrapped(*args, **kwargs)


async def async_send_wrapper(wrapped, instance, args, kwargs):
    request = bind_request(*args, **kwargs)

    with ExternalTrace("httpx", str(request.url), request.method, source=wrapped) as tracer:
        if hasattr(tracer, "generate_request_headers"):
            request._nr_trace = tracer
            outgoing_headers = tracer.generate_request_headers(tracer.transaction)
            for header_name, header_value in outgoing_headers:
                # User headers should override our CAT headers
                if header_name not in request.headers:
                    request.headers[header_name] = header_value

        return await wrapped(*args, **kwargs)


def create_nr_first_event_hooks(is_async=False):
    @property
    def nr_first_event_hooks(self):
        if not hasattr(self, "_nr_event_hooks"):
            # This branch should only be hit if agent initialize is called after
            # the initialization of the http client
            self._event_hooks = vars(self)["_event_hooks"]
            del vars(self)["_event_hooks"]
        return self._nr_event_hooks

    @nr_first_event_hooks.setter
    def nr_first_event_hooks(self, value):
        value = NewRelicFirstDict(value, is_async=is_async)
        self._nr_event_hooks = value

    return nr_first_event_hooks


def instrument_httpx_client(module):
    module.Client._event_hooks = create_nr_first_event_hooks(is_async=False)
    module.AsyncClient._event_hooks = create_nr_first_event_hooks(is_async=True)

    wrap_function_wrapper(module, "Client.send", sync_send_wrapper)
    wrap_function_wrapper(module, "AsyncClient.send", async_send_wrapper)
