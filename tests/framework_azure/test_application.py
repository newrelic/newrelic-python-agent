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
# import os
# import pathlib
# import random
# import socket
# import subprocess
# import time

# import pytest
import requests

# from testing_support.validators.validate_transaction_metrics import (
#     validate_transaction_metrics,
# )

# from urllib.request import urlopen

# from azure_functions_worker import main

# from newrelic.api.web_transaction import web_transaction

# from azure_functions_worker.main import start_async
# from azure_functions_worker.utils.dependency import DependencyManager

# from testing_support.db_settings import azurefunction_settings
# from testing_support.util import instance_hostname


# @validate_transaction_metrics(
#     "test_application:test_ping",
#     group="AzureFunction",
#     # scoped_metrics=_test_application_index_scoped_metrics
# )
# @web_transaction(name="test_application:test_ping", group="AzureFunction")
def test_ping():
    response = requests.get("http://127.0.0.1:8080/basic?user=Reli")
    assert requests.get("http://127.0.0.1:8080").status_code == 200
    # response = requests.get("http://127.0.0.1:7071/basic?user=Reli")
    assert response.status_code == 200
    assert response.text == "Hello, Reli!"
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"


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

# def azure_start():
#     DependencyManager.initialize()
#     DependencyManager.use_worker_dependencies()

#     return asyncio.run(
#         start_async(
#             "127.0.0.1",
#             PORT,
#             "8663d118-7e07-4d53-a1d0-064a8f185940",
#             "7cdc5d8d-6109-435a-b329-5a7a2e71af9f",
#         )
#     )


# def test_send_request():
#     azure_start()
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


# def available_port():
#     """
#     Get an available port on the local machine.
#     """
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.bind(("", 0))
#     port = sock.getsockname()[1]
#     sock.close()
#     return port


# # @pytest.fixture(autouse=True, scope="module")
# # def func_start_storage_emulator():
# #     # Emulate storage
# #     subprocess.Popen(["azurite", "--tableHost", "127.0.0.1"])


# # PORT = available_port()
# PORT = 7071


# # @validate_transaction_metrics(
# #     "function_app:basic_page",
# #     group="AzureFunction",
# #     # scoped_metrics=_test_application_index_scoped_metrics
# # )
# # @pytest.fixture(autouse=True, scope="module")
# def func_start_dispatcher():
#     # azure_function_command = os.path.join(os.environ["TOX_ENV_DIR"], "bin", "func")
#     # azure_function_command = "func"

#     # cmd = ["cd", f"{os.getcwd()}/tests/framework_azure/", "&&", "func", "start"] #, "--port", str(PORT)]
#     cmd = ["func", "start"]  # , "--port", str(PORT)]
#     # cmd = ["cd", f"{os.environ.get('TOX_ENV_DIR')}/tests/framework_azure", "&&", "func", "start", "--port", str(PORT)]
#     cmd_str = " ".join(cmd)
#     # cmd = f"cd tests/framework_azure && newrelic-admin run-program func start --port {str(PORT)}"

#     try:
#         # runs but on different process from instrumentation.
#         # We need to do this, but somehow on the same process
#         # subprocess.Popen(cmd_str, shell=True, env=os.environ, cwd=f"{os.getcwd()}") # nosec # also passes but diff process
#         subprocess.Popen(cmd, env=os.environ, cwd=f"{os.getcwd()}")  # passes, but diff process
#         # subprocess.run(cmd, shell=True, env=os.environ) # nosec
#         # os.system(cmd_str)  # nosec

#     except Exception as e:
#         print(f"Error: {e}")


# # @validate_transaction_metrics(
# #     "function_app:basic_page",
# #     group="AzureFunction",
# #     # scoped_metrics=_test_application_index_scoped_metrics
# # )
# def test_basic_function():
#     # @validate_transaction_metrics(
#     #     "function_app:basic_page",
#     #     group="AzureFunction",
#     #     # scoped_metrics=_test_application_index_scoped_metrics
#     # )
#     # def _test():
#     #     func_start_dispatcher()

#     # _test()
#     func_start_dispatcher()
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
#     # response = requests.get(f"http://127.0.0.1:{PORT}/basic?user=Bradlington")
#     # assert response.status_code == 200
#     # assert response.text == "Hello, Bradlington!"
#     # assert response.headers["Content-Type"] == "text/plain"


# def get_open_port():
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.bind(("", 0))
#     port = s.getsockname()[1]
#     s.close()
#     return port


# # DependencyManager.initialize()
# # DependencyManager.use_worker_dependencies()

# @pytest.fixture(autouse=True, scope="module")
# def target_dispatcher():
#     return asyncio.run(
#         start_async(
#             host="127.0.0.1",
#             port=get_open_port(),
#             worker_id="deadbeef-cafe-10c8-ba11-50de7ec7ab1e",
#             request_id="ba5eba11-ba5e-bead-5elf-affab1e0babe",
#         )
#     )
