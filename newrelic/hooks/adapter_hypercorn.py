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
from newrelic.api.asgi_application import ASGIApplicationWrapper
from newrelic.common.object_wrapper import wrap_function_wrapper


def bind_worker_serve(app, *args, **kwargs):
    return app, args, kwargs


async def wrap_worker_serve(wrapped, instance, args, kwargs):
    app, args, kwargs = bind_worker_serve(*args, **kwargs)
    app = ASGIApplicationWrapper(app)
    return await wrapped(app, *args, **kwargs)


def instrument_hypercorn_asyncio_run(module):
    wrap_function_wrapper(module, "worker_serve", wrap_worker_serve)


def instrument_hypercorn_trio_run(module):
    wrap_function_wrapper(module, "worker_serve", wrap_worker_serve)
