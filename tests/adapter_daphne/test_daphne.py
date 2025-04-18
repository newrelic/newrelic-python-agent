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
import threading

import daphne.server
import niquests
import pytest
from testing_support.certs import CERT_PATH
from testing_support.fixtures import (
    override_application_settings,
    raise_background_exceptions,
    wait_for_background_threads,
)
from testing_support.http_23_testing import make_request
from testing_support.sample_asgi_applications import AppWithCall, AppWithCallRaw, simple_app_v2_raw, simple_app_v3
from testing_support.util import get_open_port
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version, get_package_version_tuple

DAPHNE_VERSION = get_package_version_tuple("daphne")
skip_asgi_3_unsupported = pytest.mark.skipif(DAPHNE_VERSION < (3, 0), reason="ASGI3 unsupported")
skip_asgi_2_unsupported = pytest.mark.skipif(DAPHNE_VERSION >= (3, 0), reason="ASGI2 unsupported")


@pytest.fixture(
    params=(
        pytest.param(simple_app_v2_raw, marks=skip_asgi_2_unsupported),
        pytest.param(simple_app_v3, marks=skip_asgi_3_unsupported),
        pytest.param(AppWithCallRaw(), marks=skip_asgi_3_unsupported),
        pytest.param(AppWithCall(), marks=skip_asgi_3_unsupported),
    ),
    ids=("raw", "wrapped", "class_with_call", "class_with_call_double_wrapped"),
)
def app(request, server_and_port):
    app = request.param
    server, _ = server_and_port
    server.application = app
    return app


@pytest.fixture(scope="session")
def port(server_and_port):
    _, port = server_and_port
    return port


@pytest.fixture(scope="session")
def server_and_port():
    port = get_open_port()

    servers = []
    loops = []
    ready = threading.Event()

    def server_run():
        def on_ready():
            if not ready.is_set():
                loops.append(asyncio.get_event_loop())
                servers.append(server)
                ready.set()

        async def fake_app(*args, **kwargs):
            raise RuntimeError("Failed to swap out app.")

        server = daphne.server.Server(
            fake_app,
            endpoints=[f"ssl:{port}:privateKey={CERT_PATH}:certKey={CERT_PATH}:interface=127.0.0.1"],
            ready_callable=on_ready,
            signal_handlers=False,
            verbosity=9,
        )

        server.run()

    thread = threading.Thread(target=server_run, daemon=True)
    thread.start()
    assert ready.wait(timeout=10)
    yield servers[0], port

    reactor = daphne.server.reactor
    _ = [loop.call_soon_threadsafe(reactor.stop) for loop in loops]  # Stop all loops
    thread.join(timeout=10)

    if thread.is_alive():
        raise RuntimeError("Thread failed to exit in time.")


@pytest.mark.parametrize("http_version", [1, 2], ids=["HTTP/1", "HTTP/2"])
@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_daphne_200(port, app, http_version):
    daphne_version = get_package_version("daphne")
    assert daphne_version is not None

    @validate_transaction_metrics(
        callable_name(app), custom_metrics=[(f"Python/Dispatcher/Daphne/{daphne_version}", 1)]
    )
    @raise_background_exceptions()
    @wait_for_background_threads()
    def response():
        return make_request(host="localhost", port=port, path="/", http_version=http_version, timeout=10)

    response().raise_for_status()


@pytest.mark.parametrize("http_version", [1, 2], ids=["HTTP/1", "HTTP/2"])
@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_daphne_500(port, app, http_version):
    @validate_transaction_errors(["builtins:ValueError"])
    @validate_transaction_metrics(callable_name(app))
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        with pytest.raises(niquests.exceptions.HTTPError):
            make_request(host="localhost", port=port, path="/exc", http_version=http_version, timeout=10)

    _test()
