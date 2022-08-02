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

import time
import asyncio

import threading
from urllib.request import HTTPError, urlopen

import pytest
from testing_support.fixture.event_loop import event_loop as loop
from testing_support.fixtures import (
    override_application_settings,
    raise_background_exceptions,
    validate_transaction_errors,
    validate_transaction_metrics,
    wait_for_background_threads,
)
from testing_support.sample_asgi_applications import (
    AppWithCall,
    AppWithCallRaw,
    simple_app_v2_raw,
)
from testing_support.util import get_open_port

from newrelic.common.object_names import callable_name

@pytest.fixture(
    params=(
            simple_app_v2_raw,
            AppWithCallRaw(),
            AppWithCall(),
    ),
    ids=("raw", "class_with_call", "class_with_call_double_wrapped"),
)
def app(request):
    return request.param


@pytest.fixture()
def port(loop, app):
    import hypercorn.asyncio
    import hypercorn.config

    port = get_open_port()
    shutdown = asyncio.Event()

    def server_run():
        async def shutdown_trigger():
            await shutdown.wait()
            return True

        config = hypercorn.config.Config.from_mapping({
            "bind": ["127.0.0.1:%d" % port],
        })

        try:
            loop.run_until_complete(hypercorn.asyncio.serve(app, config, shutdown_trigger=shutdown_trigger))
        except Exception:
            pass

    thread = threading.Thread(target=server_run, daemon=True)
    thread.start()
    wait_for_port(port, 10)
    yield port

    shutdown.set()
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=10)

    if thread.is_alive():
        raise RuntimeError("Thread failed to exit in time.")


def wait_for_port(port, retries=10):
    for _ in range(retries):
        try:
            assert urlopen("http://localhost:%d" % port, timeout=1).status == 200
            return
        except Exception:
            pass
        
        time.sleep(1)

    raise RuntimeError("Failed to wait for port %d" % port)


@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_hypercorn_200(port, app):
    @validate_transaction_metrics(callable_name(app))
    @raise_background_exceptions()
    @wait_for_background_threads()
    def response():
        return urlopen("http://localhost:%d" % port, timeout=10)

    assert response().status == 200


@override_application_settings({"transaction_name.naming_scheme": "framework"})
@validate_transaction_errors(["builtins:ValueError"])
def test_hypercorn_500(port, app):
    @validate_transaction_metrics(callable_name(app))
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        try:
            urlopen("http://localhost:%d/exc" % port)
        except HTTPError:
            pass

    _test()
