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

from newrelic.common.object_wrapper import wrap_function_wrapper
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import current_transaction


def bind_request(request, *args, **kwargs):
    return request


def sync_send_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    request = bind_request(*args, **kwargs)
    connection = instance

    with ExternalTrace('httpx', str(request.url), request.method) as tracer:
        # Add the tracer to the connection object. The tracer will be
        # used in getresponse() to add back into the external trace,
        # after the trace has already completed, details from the
        # response headers.
        if hasattr(tracer, 'generate_request_headers'):
            outgoing_headers = dict(tracer.generate_request_headers(transaction))

            # Preserve existing headers and add our outgoing headers
            client_headers = request.headers
            client_headers.update(outgoing_headers)
            request.headers = client_headers

            connection._nr_external_tracer = tracer

        return wrapped(*args, **kwargs)


async def async_send_wrapper(wrapped, instance, args, kwargs):
    transaction = current_transaction()
    request = bind_request(*args, **kwargs)
    connection = instance

    with ExternalTrace('httpx', str(request.url), request.method) as tracer:
        # Add the tracer to the connection object. The tracer will be
        # used in getresponse() to add back into the external trace,
        # after the trace has already completed, details from the
        # response headers.
        if hasattr(tracer, 'generate_request_headers'):
            outgoing_headers = dict(tracer.generate_request_headers(transaction))

            # Preserve existing headers and add our outgoing headers
            client_headers = request.headers
            client_headers.update(outgoing_headers)
            request.headers = client_headers

            connection._nr_external_tracer = tracer

        return await wrapped(*args, **kwargs)


def instrument_httpx_client(module):
    wrap_function_wrapper(module, "Client.send", sync_send_wrapper)
    wrap_function_wrapper(module, "AsyncClient.send", async_send_wrapper)
