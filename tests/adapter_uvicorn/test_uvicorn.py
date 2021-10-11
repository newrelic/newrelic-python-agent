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

import asyncio
import logging
import socket
import threading
from urllib.request import HTTPError, urlopen

import pytest
import uvicorn
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
from uvicorn.config import Config
from uvicorn.main import Server

from newrelic.common.object_names import callable_name

UVICORN_VERSION = tuple(int(v) for v in uvicorn.__version__.split(".")[:2])


def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(
    params=(
        simple_app_v2_raw,
        pytest.param(
            AppWithCallRaw(),
            marks=pytest.mark.skipif(UVICORN_VERSION < (0, 6), reason="ASGI3 unsupported"),
        ),
        pytest.param(
            AppWithCall(),
            marks=pytest.mark.skipif(UVICORN_VERSION < (0, 6), reason="ASGI3 unsupported"),
        ),
    ),
    ids=("raw", "class_with_call", "class_with_call_double_wrapped"),
)
def app(request):
    return request.param


@pytest.fixture
def port(app):
    port = get_open_port()

    loops = []
    ready = threading.Event()

    def server_run():
        def on_tick_sync():
            if not ready.is_set():
                loops.append(asyncio.get_event_loop())
                ready.set()

        async def on_tick():
            on_tick_sync()

        config = Config(app, host="127.0.0.1", port=port, loop="asyncio")
        config.callback_notify = on_tick
        config.log_config = {"version": 1}
        config.disable_lifespan = True
        config.logger = logging.getLogger("uvicorn")
        server = Server(config=config)
        server.install_signal_handlers = lambda *args, **kwargs: None
        try:
            server.started.set = on_tick_sync
        except Exception:
            pass
        server.run()

    thread = threading.Thread(target=server_run, daemon=True)
    thread.start()
    ready.wait()
    yield port
    _ = [loop.stop() for loop in loops]  # Stop all loops
    thread.join(timeout=1)

    if thread.is_alive():
        raise RuntimeError("Thread failed to exit in time.")


@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_uvicorn_200(port, app):
    @validate_transaction_metrics(callable_name(app))
    @raise_background_exceptions()
    @wait_for_background_threads()
    def response():
        return urlopen("http://localhost:%d" % port)

    assert response().status == 200


@override_application_settings({"transaction_name.naming_scheme": "framework"})
@validate_transaction_errors(["builtins:ValueError"])
def test_uvicorn_500(port, app):
    @validate_transaction_metrics(callable_name(app))
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        try:
            urlopen("http://localhost:%d/exc" % port)
        except HTTPError:
            pass

    _test()
