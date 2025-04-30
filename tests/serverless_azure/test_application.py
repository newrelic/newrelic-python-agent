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
import os
import requests
import subprocess
import socket
import time
# from testing_support.db_settings import azurefunction_settings

# from testing_support.validators.validate_transaction_metrics import (
#     validate_transaction_metrics,
# )

# DB_SETTINGS = azurefunction_settings()[0]
# AZURE_HOST = DB_SETTINGS["host"]
# AZURE_PORT = DB_SETTINGS["port"]


# Metric checks example:
# INSTANCE_METRIC_HOST = system_info.gethostname() if MONGODB_HOST == "127.0.0.1" else MONGODB_HOST
# INSTANCE_METRIC_NAME = f"Datastore/instance/MongoDB/{INSTANCE_METRIC_HOST}/{MONGODB_PORT}"

# @validate_transaction_metrics(
#     "test_application:test_ping",
#     group="AzureFunction",
#     # scoped_metrics=_test_application_index_scoped_metrics
# )
# @web_transaction(name="test_application:test_ping", group="AzureFunction")
# def old_test_ping():
#     response = requests.get(f"http://{AZURE_HOST}:{AZURE_PORT}/basic?user=Reli")
#     assert response.status_code == 200
#     assert response.text == "Hello, Reli!"
#     assert response.headers["Content-Type"] == "text/plain"


def azure_start():
    # Start the Azure Function app using subprocess
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = ["func", "start"]
    process = subprocess.Popen(cmd, cwd=f"{cur_dir}/sample_application")
    return process


def azure_end(process):
    # Terminate the Azure Function app process
    process.terminate()


def test_ping():
    # Start the Azure Function app
    process = azure_start()

    # Wait until the connection is established before making the request.
    for _ in range(50):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", 7071))
            sock.close()
            break
        except (socket.error, ConnectionRefusedError) as e:
            pass

        time.sleep(0.5)

    # Send a request to the Azure Function app
    response = requests.get(f"http://localhost:7071/basic?user=Reli+5Ever")
    assert response.status_code == 200
    assert response.text == "Hello, Reli 5Ever!"
    assert response.headers["Content-Type"] == "text/plain"
        
    azure_end(process)

