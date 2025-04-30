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

# import pytest
import requests
from testing_support.db_settings import azurefunction_settings

# from testing_support.validators.validate_transaction_metrics import (
#     validate_transaction_metrics,
# )

DB_SETTINGS = azurefunction_settings()[0]
AZURE_HOST = DB_SETTINGS["host"]
AZURE_PORT = DB_SETTINGS["port"]


# Metric checks example:
# INSTANCE_METRIC_HOST = system_info.gethostname() if MONGODB_HOST == "127.0.0.1" else MONGODB_HOST
# INSTANCE_METRIC_NAME = f"Datastore/instance/MongoDB/{INSTANCE_METRIC_HOST}/{MONGODB_PORT}"

# @validate_transaction_metrics(
#     "test_application:test_ping",
#     group="AzureFunction",
#     # scoped_metrics=_test_application_index_scoped_metrics
# )
# @web_transaction(name="test_application:test_ping", group="AzureFunction")
def test_ping():
    response = requests.get(f"http://{AZURE_HOST}:{AZURE_PORT}/basic?user=Reli")
    assert response.status_code == 200
    assert response.text == "Hello, Reli!"
    assert response.headers["Content-Type"] == "text/plain"


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
