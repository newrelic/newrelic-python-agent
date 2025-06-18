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
import os
import queue
import sys
import threading
import time
from pathlib import Path

import azure_functions_worker.dispatcher
import pytest

from .messages import do_worker_startup_events

DISPATCHER = None
DISPATCHER_TASK = None
DISPATCHER_READY_EVENT = threading.Event()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class MockDispatcher(azure_functions_worker.dispatcher.Dispatcher):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_queue = self._grpc_resp_queue  # Alias for testing
        self.request_queue = queue.Queue()  # Also use a queue here for mocking
        self.__closed = False  # Set this to close dispatcher gracefully

    def stop(self):
        self.__closed = True
        super().stop()
        DISPATCHER_TASK.cancel()  # Cancel the dispatcher task if running

    def _Dispatcher__poll_grpc(self, *args, **kwargs):
        # Unblock startup by setting this future result
        self._loop.call_soon_threadsafe(self._grpc_connected_fut.set_result, True)

        # Pull from request queue and dispatch requests
        while not self.__closed:
            try:
                request = self.request_queue.get(timeout=1.0)
            except queue.Empty:
                pass
            else:
                # Simulate receiving a request and dispatching it
                self._loop.call_soon_threadsafe(self._loop.create_task, self._dispatch_grpc_request(request))

    async def dispatch_forever(self):
        try:
            await super().dispatch_forever()
        except Exception:
            logger.exception("Error in dispatch_forever")
            raise

        logger.info("MockDispatcher dispatch_forever completed.")

    # Custom methods
    def _send_event(self, event, response_type):
        self.request_queue.put(event)
        response = self._wait_for_response(response_type, timeout=30.0)
        return response

    def _wait_for_response(self, response_type, timeout=30):
        elapsed = 0.0
        while True:
            if elapsed >= timeout:
                raise RuntimeError("Timeout waiting for queue item.")

            try:
                item = self.response_queue.get(block=False)
            except queue.Empty:
                time.sleep(1.0)
                elapsed += 1.0
            else:
                # Only return the response if it's the expected type, otherwise continue waiting
                if item.HasField(response_type):
                    return item


def start_dispatcher_thread():
    """Start the worker on a separate thread and returns the dispatcher instance."""

    async def _run_dispatcher_event_loop():
        global DISPATCHER, DISPATCHER_TASK

        # Change working directory to the directory of this file to make function loading work correctly
        file_dir = Path(__file__).parent
        os.chdir(file_dir)
        sys.path.append(str(file_dir))

        # Create a Dispatcher instance, which will call poll_grpc() in the event loop
        DISPATCHER = await MockDispatcher.connect(
            host="localhost", port=1234, worker_id="worker_id", request_id="request_id", connect_timeout=5.0
        )

        # Start the dispatcher in the event loop without blocking
        DISPATCHER_TASK = DISPATCHER._loop.create_task(DISPATCHER.dispatch_forever())
        DISPATCHER_READY_EVENT.set()
        await DISPATCHER_TASK

    # Start the dispatcher in a separate thread
    dispatcher_thread = threading.Thread(target=lambda: asyncio.run(_run_dispatcher_event_loop()), daemon=True)
    dispatcher_thread.start()

    # Wait for the dispatcher thread to create the dispatcher
    DISPATCHER_READY_EVENT.wait(timeout=10.0)

    # Run the worker startup events to load the function
    do_worker_startup_events(DISPATCHER)

    return DISPATCHER
