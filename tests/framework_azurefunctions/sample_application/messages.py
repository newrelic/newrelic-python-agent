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

import logging
from pathlib import Path
from uuid import uuid4

from azure_functions_worker.protos.FunctionRpc_pb2 import (
    BindingInfo,
    FunctionLoadRequest,
    FunctionsMetadataRequest,
    InvocationRequest,
    ParameterBinding,
    RpcFunctionMetadata,
    StreamingMessage,
    TypedData,
    WorkerInitRequest,
)

logger = logging.getLogger(__name__)

FILE_DIR = Path(__file__).parent

uuid = lambda: str(uuid4())
FUNCTION_ID_SYNC = uuid()
FUNCTION_ID_ASYNC = uuid()

worker_init_request = StreamingMessage(
    request_id=uuid(),
    worker_init_request=WorkerInitRequest(
        host_version="4.1036.1.23224",
        capabilities={"MultiStream": "10"},
        worker_directory=str(FILE_DIR),
        function_app_directory=str(FILE_DIR),
    ),
)

functions_metadata_request = StreamingMessage(
    request_id=uuid(), functions_metadata_request={"function_app_directory": str(FILE_DIR)}
)

function_load_request_sync = StreamingMessage(
    request_id=uuid(),
    function_load_request=FunctionLoadRequest(
        function_id=FUNCTION_ID_SYNC,
        metadata=RpcFunctionMetadata(
            name="HttpTriggerSync",
            directory=str(FILE_DIR),
            script_file="function_app.py",
            entry_point="HttpTriggerSync",
            bindings={"req": BindingInfo(type="httpTrigger"), "$return": BindingInfo(type="http", direction="out")},
            properties={"worker_indexed": "True", "FunctionId": FUNCTION_ID_SYNC},
        ),
    ),
)

function_load_request_async = StreamingMessage(
    request_id=uuid(),
    function_load_request=FunctionLoadRequest(
        function_id=FUNCTION_ID_ASYNC,
        metadata=RpcFunctionMetadata(
            name="HttpTriggerAsync",
            directory=str(FILE_DIR),
            script_file="function_app.py",
            entry_point="HttpTriggerAsync",
            bindings={"req": BindingInfo(type="httpTrigger"), "$return": BindingInfo(type="http", direction="out")},
            properties={"worker_indexed": "True", "FunctionId": FUNCTION_ID_ASYNC},
        ),
    ),
)


invocation_request_sync = StreamingMessage(
    request_id=uuid(),
    invocation_request=InvocationRequest(
        invocation_id=uuid(),
        function_id=FUNCTION_ID_SYNC,
        input_data=[
            ParameterBinding(
                name="req",
                data={
                    "http": {
                        "method": "GET",
                        "url": "http://127.0.0.1:7071/sync?user=Reli",
                        "headers": {
                            "user-agent": "python-requests/2.32.4",
                            "host": "127.0.0.1:7071",
                            "connection": "keep-alive",
                            "accept": "*/*",
                            "accept-encoding": "gzip, deflate",
                        },
                        "query": {"user": "Reli"},
                    }
                },
            )
        ],
        trigger_metadata={
            "user": TypedData(string="Reli"),
            "Query": TypedData(json='{"user":"Reli"}'),
            "Headers": TypedData(
                json='{"Accept":"*/*","Connection":"keep-alive","Host":"127.0.0.1:7071","User-Agent":"python-requests/2.32.4","Accept-Encoding":"gzip, deflate"}'
            ),
        },
    ),
)

invocation_request_async = StreamingMessage(
    request_id=uuid(),
    invocation_request=InvocationRequest(
        invocation_id=uuid(),
        function_id=FUNCTION_ID_ASYNC,
        input_data=[
            ParameterBinding(
                name="req",
                data={
                    "http": {
                        "method": "GET",
                        "url": "http://127.0.0.1:7071/async?user=Reli",
                        "headers": {
                            "user-agent": "python-requests/2.32.4",
                            "host": "127.0.0.1:7071",
                            "connection": "keep-alive",
                            "accept": "*/*",
                            "accept-encoding": "gzip, deflate",
                        },
                        "query": {"user": "Reli"},
                    }
                },
            )
        ],
        trigger_metadata={
            "user": TypedData(string="Reli"),
            "Query": TypedData(json='{"user":"Reli"}'),
            "Headers": TypedData(
                json='{"Accept":"*/*","Connection":"keep-alive","Host":"127.0.0.1:7071","User-Agent":"python-requests/2.32.4","Accept-Encoding":"gzip, deflate"}'
            ),
        },
    ),
)


def do_worker_startup_events(dispatcher):
    from azure_functions_worker.logging import enable_console_logging

    enable_console_logging()

    global FUNCTION_ID_ASYNC, FUNCTION_ID_SYNC

    # =================
    # WorkerInitRequest
    # =================
    response = dispatcher._send_event(worker_init_request, "worker_init_response")
    assert response.worker_init_response.result.status == 1, "Worker initialization failed."

    # =======================
    # FunctionMetadataRequest
    # =======================
    response = dispatcher._send_event(functions_metadata_request, "function_metadata_response")
    assert response.function_metadata_response.result.status == 1, "Function parsing failed."
    function_metadata = response.function_metadata_response.function_metadata_results

    # =========================
    # FunctionLoadRequest(Sync)
    # =========================
    # Generate FunctionLoadRequest payload using the returned metadata
    sync_metadata = [m for m in function_metadata if m.name == "HttpTriggerSync"][0]
    FUNCTION_ID_SYNC = sync_metadata.function_id
    function_load_request_sync = StreamingMessage(
        request_id=uuid(),
        function_load_request=FunctionLoadRequest(function_id=FUNCTION_ID_SYNC, metadata=sync_metadata),
    )

    response = dispatcher._send_event(function_load_request_sync, "function_load_response")
    assert response.function_load_response.result.status == 1, "Failed to load function."

    # ==========================
    # FunctionLoadRequest(Async)
    # ==========================
    # Generate FunctionLoadRequest payload using the returned metadata
    async_metadata = [m for m in function_metadata if m.name == "HttpTriggerAsync"][0]
    FUNCTION_ID_ASYNC = async_metadata.function_id
    function_load_request_async = StreamingMessage(
        request_id=uuid(),
        function_load_request=FunctionLoadRequest(function_id=FUNCTION_ID_ASYNC, metadata=async_metadata),
    )

    response = dispatcher._send_event(function_load_request_async, "function_load_response")
    assert response.function_load_response.result.status == 1, "Failed to load function."


def send_invocation_event(dispatcher, user="Reli", is_async=False):
    if is_async:
        function_id = FUNCTION_ID_ASYNC
        invocation_request = invocation_request_async
    else:
        function_id = FUNCTION_ID_SYNC
        invocation_request = invocation_request_sync

    # =================
    # InvocationRequest
    # =================
    invocation_request.invocation_request.function_id = function_id  # Set the function ID from previous metadata
    invocation_request.invocation_request.input_data[0].data.http.query["user"] = user

    response = dispatcher._send_event(invocation_request, "invocation_response")

    return response
