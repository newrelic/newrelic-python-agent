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
import logging
import socket
import threading

import moto.server
import werkzeug.serving
from testing_support.fixture.event_loop import (  # noqa: F401, pylint: disable=W0611
    event_loop as loop,
)
from testing_support.fixtures import (  # noqa: F401, pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

PORT = 4443
AWS_ACCESS_KEY_ID = "AAAAAAAAAAAACCESSKEY"
AWS_SECRET_ACCESS_KEY = "AAAAAASECRETKEY"  # nosec
HOST = "127.0.0.1"


_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}
collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (external_aiobotocore)",
    default_settings=_default_settings,
    linked_applications=["Python Agent Test (external_aiobotocore)"],
)


def get_free_tcp_port(release_socket: bool = False):
    sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sckt.bind((HOST, 0))
    _, port = sckt.getsockname()  # address, port
    if release_socket:
        sckt.close()
        return port

    return sckt, port


class MotoService:
    """Will Create MotoService.
    Service is ref-counted so there will only be one per process. Real Service will
    be returned by `__aenter__`."""

    _services = {}  # {name: instance}

    def __init__(self, service_name: str, port: int = None, ssl: bool = False):
        self._service_name = service_name

        if port:
            self._socket = None
            self._port = port
        else:
            self._socket, self._port = get_free_tcp_port()

        self._thread = None
        self._logger = logging.getLogger("MotoService")
        self._refcount = None
        self._ip_address = HOST
        self._server = None
        self._ssl_ctx = werkzeug.serving.generate_adhoc_ssl_context() if ssl else None
        self._schema = "http" if not self._ssl_ctx else "https"

    @property
    def endpoint_url(self):
        return f"{self._schema}://{self._ip_address}:{self._port}"

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            await self._start()
            try:
                result = await func(*args, **kwargs)
            finally:
                await self._stop()
            return result

        functools.update_wrapper(wrapper, func)
        wrapper.__wrapped__ = func
        return wrapper

    async def __aenter__(self):
        svc = self._services.get(self._service_name)
        if svc is None:
            self._services[self._service_name] = self
            self._refcount = 1
            await self._start()
            return self
        else:
            svc._refcount += 1
            return svc

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._refcount -= 1

        if self._socket:
            self._socket.close()
            self._socket = None

        if self._refcount == 0:
            del self._services[self._service_name]
            await self._stop()

    def _server_entry(self):
        self._main_app = moto.server.DomainDispatcherApplication(
            moto.server.create_backend_app  # , service=self._service_name
        )
        self._main_app.debug = True

        if self._socket:
            self._socket.close()  # release right before we use it
            self._socket = None

        self._server = werkzeug.serving.make_server(
            self._ip_address,
            self._port,
            self._main_app,
            True,
            ssl_context=self._ssl_ctx,
        )
        self._server.serve_forever()

    async def _start(self):
        self._thread = threading.Thread(target=self._server_entry, daemon=True)
        self._thread.start()

    async def _stop(self):
        if self._server:
            self._server.shutdown()

        self._thread.join()
