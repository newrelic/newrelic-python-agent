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

# import asyncio
import os

# import pytest
# import pathlib
# import random
import socket
import subprocess
import time

import requests

# from urllib.request import urlopen


# from azure_functions_worker import main

# from newrelic.api.web_transaction import web_transaction

# from azure_functions_worker.main import start_async
# from azure_functions_worker.utils.dependency import DependencyManager

# from testing_support.db_settings import azurefunction_settings
# from testing_support.util import instance_hostname

# from testing_support.validators.validate_transaction_metrics import (
#     validate_transaction_metrics,
# )


# ATTEMPT #3

# def available_port():
#     """
#     Get an available port on the local machine.
#     """
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.bind(("", 0))
#     port = sock.getsockname()[1]
#     sock.close()
#     return port

# # PORT = available_port()
# PORT = 7071

# def test_azure_start():
#     return asyncio.run(
#         start_async(
#             "localhost",
#             PORT,
#             "8663d118-7e07-4d53-a1d0-064a8f185940",
#             "7cdc5d8d-6109-435a-b329-5a7a2e71af9f",
#         )
#     )


# def send_request():
#     # Wait until the connection is established before making the request.
#     for _ in range(50):
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         try:
#             sock.connect(("127.0.0.1", PORT))
#             sock.close()
#             break
#         except (socket.error, ConnectionRefusedError) as e:
#             pass

#         time.sleep(0.5)

#     response = requests.get(f"http://127.0.0.1:{PORT}/basic?user=Reli")
#     assert response.status_code == 200
#     assert response.text == "Hello, Reli!"
#     assert response.headers["Content-Type"] == "text/plain"


# ATTEMPT #2

# Maybe subprocess.run(func start) function to be listened to for transaction
# then curl/requests in another process to test the function app.


def available_port():
    """
    Get an available port on the local machine.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class TerminatingPopen(subprocess.Popen):
    """Context manager will terminate process when exiting, instead of waiting."""

    def __enter__(self):
        return self

    def __exit__(self, exc, val, tb):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()

        self.terminate()


PORT = available_port()
# PORT = 7071


# @validate_transaction_metrics(
#     "function_app:basic_page",
#     group="AzureFunction",
#     # scoped_metrics=_test_application_index_scoped_metrics
# )
# @pytest.fixture(autouse=True, scope="module")
def func_start_dispatcher():

    # azure_function_command = os.path.join(os.environ["TOX_ENV_DIR"], "bin", "func")
    # azure_function_command = "func"

    cmd = ["cd", f"{os.environ['PWD']}/tests/framework_azure", "&&", "func", "start", "--port", str(PORT)]
    cmd_str = " ".join(cmd)
    # cmd = f"cd tests/framework_azure && newrelic-admin run-program func start --port {str(PORT)}"

    try:
        # runs but on different process from instrumentation.
        # We need to do this, but somehow on the same process
        # subprocess.Popen(cmd_str, shell=True, env=os.environ)
        # subprocess.run(cmd, shell=True, env=os.environ)
        os.system(cmd_str)  # nosec

    except Exception as e:
        print(f"Error: {e}")


# @validate_transaction_metrics(
#     "function_app:basic_page",
#     group="AzureFunction",
#     # scoped_metrics=_test_application_index_scoped_metrics
# )
def test_basic_function():
    # @validate_transaction_metrics(
    #     "function_app:basic_page",
    #     group="AzureFunction",
    #     # scoped_metrics=_test_application_index_scoped_metrics
    # )
    # def _test():
    #     func_start_dispatcher()

    # _test()
    func_start_dispatcher()
    # Wait until the connection is established before making the request.
    for _ in range(50):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", PORT))
            sock.close()
            break
        except (socket.error, ConnectionRefusedError) as e:
            pass

        time.sleep(0.5)

    response = requests.get(f"http://127.0.0.1:{PORT}/basic?user=Reli")
    assert response.status_code == 200
    assert response.text == "Hello, Reli!"
    assert response.headers["Content-Type"] == "text/plain"
    # response = requests.get(f"http://127.0.0.1:{PORT}/basic?user=Bradlington")
    # assert response.status_code == 200
    # assert response.text == "Hello, Bradlington!"
    # assert response.headers["Content-Type"] == "text/plain"


# ATTEMPT #1.  May salvage some of this code for future use.

# def get_open_port():
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.bind(("", 0))
#     port = s.getsockname()[1]
#     s.close()
#     return port


# DB_SETTINGS = azurefunction_settings()[0]
# HOST = instance_hostname(DB_SETTINGS["host"])

# # DependencyManager.initialize()
# # DependencyManager.use_worker_dependencies()

# @pytest.fixture(autouse=True, scope="module")
# def target_dispatcher():
#     return asyncio.run(
#         start_async(
#             host="127.0.0.1",   # HOST,
#             port=get_open_port(),
#             worker_id="8663d118-7e07-4d53-a1d0-064a8f185940",
#             request_id="7cdc5d8d-6109-435a-b329-5a7a2e71af9f",
#             # worker_id="deadbeef-cafe-10c8-ba11-50de7ec7ab1e",
#             # request_id="ba5eba11-ba5e-bead-5elf-affab1e0babe",
#         )
#     )


# _test_application_index_scoped_metrics = [
#     ("AzureFunction/_test_application:basic_page", 1),
# ]

# # TODO: This test is failing because the function call is not being made correctly.
# # @validate_transaction_metrics(
# #     "_test_application:basic_page",
# #     # group="AzureFunction",
# #     # scoped_metrics=_test_application_index_scoped_metrics
# # )
# def test_application_basic():
#     function_call = basic_page.build().get_user_function()
#     response = function_call(mock_http_request)
#     # response = basic_func(mock_http_request)
#     # breakpoint()
#     assert response.status_code == 200
#     assert response.get_body() == b"Hello, Reli!"
#     assert dict(response.headers) == {"Content-Type": "text/plain"}
