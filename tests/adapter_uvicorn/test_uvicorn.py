import asyncio
import functools
import logging
import socket
import threading
from urllib.request import HTTPError, urlopen

import pytest
from uvicorn.config import Config
from uvicorn.main import Server

from testing_support.fixtures import (
    override_application_settings,
    validate_transaction_errors,
    validate_transaction_metrics,
)
from testing_support.sample_asgi_applications import simple_app_v2_raw


def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def port():
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

        config = Config(simple_app_v2_raw, host="127.0.0.1", port=port, loop="asyncio")
        config.callback_notify = on_tick
        config.log_config = {"version": 1}
        config.logger = logging.getLogger("uvicorn")
        server = Server(config=config)
        server.install_signal_handlers = lambda *args, **kwargs: None
        if isinstance(server.started, type(ready)):
            server.started.set = on_tick_sync
        server.run()

    thread = threading.Thread(target=server_run)
    thread.start()
    ready.wait()
    yield port
    loops[0].stop()
    thread.join(timeout=0.2)


@override_application_settings({"transaction_name.naming_scheme": "framework"})
@validate_transaction_metrics("testing_support.sample_asgi_applications:simple_app_v2_raw")
def test_uvicorn_200(port):
    response = urlopen("http://localhost:%d" % port)
    assert response.status == 200


@override_application_settings({"transaction_name.naming_scheme": "framework"})
@validate_transaction_errors(["builtins:ValueError"])
@validate_transaction_metrics("testing_support.sample_asgi_applications:simple_app_v2_raw")
def test_uvicorn_500(port):
    try:
        urlopen("http://localhost:%d/exc" % port)
    except HTTPError:
        pass
