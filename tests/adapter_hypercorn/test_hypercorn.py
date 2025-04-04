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
import time

import niquests
import pytest
from testing_support.certs import CERT_PATH
from testing_support.fixtures import (
    override_application_settings,
    raise_background_exceptions,
    wait_for_background_threads,
)
from testing_support.http_23_testing import make_request
from testing_support.sample_asgi_applications import AppWithCall, AppWithCallRaw, simple_app_v2_raw
from testing_support.util import get_open_port
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.transaction import ignore_transaction
from newrelic.common.object_names import callable_name
from newrelic.common.package_version_utils import get_package_version, get_package_version_tuple

HYPERCORN_VERSION = get_package_version_tuple("hypercorn")
asgi_2_unsupported = HYPERCORN_VERSION >= (0, 14, 1)
wsgi_unsupported = HYPERCORN_VERSION < (0, 14, 1)


def wsgi_app(environ, start_response):
    path = environ["PATH_INFO"]

    if path == "/":
        start_response("200 OK", response_headers=[])
    elif path == "/ignored":
        ignore_transaction()
        start_response("200 OK", response_headers=[])
    elif path == "/exc":
        raise ValueError("whoopsies")

    return []


@pytest.fixture(
    scope="session",
    params=(
        pytest.param(simple_app_v2_raw, marks=pytest.mark.skipif(asgi_2_unsupported, reason="ASGI2 unsupported")),
        AppWithCallRaw(),
        AppWithCall(),
        pytest.param(wsgi_app, marks=pytest.mark.skipif(wsgi_unsupported, reason="WSGI unsupported")),
    ),
    ids=("raw", "class_with_call", "class_with_call_double_wrapped", "wsgi"),
)
def app(request):
    return request.param


@pytest.fixture(scope="session")
def port(loop, app):
    import hypercorn.asyncio
    import hypercorn.config

    port = get_open_port()
    shutdown = asyncio.Event()

    def server_run():
        async def shutdown_trigger():
            await shutdown.wait()
            return True

        config = hypercorn.config.Config.from_mapping(
            {"bind": [f"localhost:{port}"], "certfile": CERT_PATH, "keyfile": CERT_PATH}
        )

        try:
            loop.run_until_complete(hypercorn.asyncio.serve(app, config, shutdown_trigger=shutdown_trigger))
        except Exception:
            pass

    thread = threading.Thread(target=server_run, daemon=True)
    thread.start()
    wait_for_port(port)
    yield port

    shutdown.set()
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=10)

    if thread.is_alive():
        raise RuntimeError("Thread failed to exit in time.")


def wait_for_port(port, retries=10):
    status = None
    for _ in range(retries):
        try:
            status = make_request(host="localhost", port=port, path="/ignored", timeout=1).status_code
            assert status == 200
            return
        except Exception as e:
            status = e

        time.sleep(1)

    raise RuntimeError(f"Failed to wait for port {port}. Got status {status}")


@pytest.mark.parametrize("http_version", [1, 2], ids=["HTTP/1", "HTTP/2"])
@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_hypercorn_200(port, app, http_version):
    hypercorn_version = get_package_version("hypercorn")
    assert hypercorn_version is not None

    @validate_transaction_metrics(
        callable_name(app), custom_metrics=[(f"Python/Dispatcher/Hypercorn/{hypercorn_version}", 1)]
    )
    @raise_background_exceptions()
    @wait_for_background_threads()
    def response():
        return make_request(host="localhost", port=port, path="/", http_version=http_version, timeout=10)

    response().raise_for_status()


@pytest.mark.parametrize("http_version", [1, 2], ids=["HTTP/1", "HTTP/2"])
@override_application_settings({"transaction_name.naming_scheme": "framework"})
def test_hypercorn_500(port, app, http_version):
    @validate_transaction_errors(["builtins:ValueError"])
    @validate_transaction_metrics(callable_name(app))
    @raise_background_exceptions()
    @wait_for_background_threads()
    def _test():
        with pytest.raises(niquests.exceptions.HTTPError):
            make_request(host="localhost", port=port, path="/exc", http_version=http_version, timeout=10)

    _test()
