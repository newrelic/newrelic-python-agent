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

import os
import requests
import subprocess
import socket
import time


def azure_start():
    nr_env = os.environ.copy()
    nr_env["NEW_RELIC_STARTUP_TIMEOUT"] = "10.0"
    # Start the Azure Function app using subprocess
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = ["func", "start"]
    process = subprocess.Popen(cmd, cwd=f"{cur_dir}/sample_application", env=nr_env)
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
            sock.connect((f"127.0.0.1", 7071))
            sock.close()
            break
        except (socket.error, ConnectionRefusedError) as e:
            pass

        time.sleep(0.5)

    # Send a request to the Azure Function app
    response = requests.get(f"http://127.0.0.1:7071/basic?user=Reli")
    assert response.status_code == 200
    assert response.text == "Hello, Reli!"
    assert response.headers["Content-Type"] == "text/plain"
        
    azure_end(process)

