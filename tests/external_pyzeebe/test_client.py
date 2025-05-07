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

import pytest

from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from _dummy_client import create_dummy_client

CLIENT_GROUP = "ZeebeClient"

# Test ZeebeClient.run_process
@validate_transaction_metrics(
    f"OtherTransaction/{CLIENT_GROUP}/run_process",
    scoped_metrics=[],
    rollup_metrics=[
        ("OtherTransaction/all", 1),
        (f"OtherTransaction/{CLIENT_GROUP}/all", 1),
        (f"OtherTransaction/{CLIENT_GROUP}/run_process", 1),
    ],
    background_task=True,
)
@pytest.mark.asyncio
async def test_run_process_outside(pyzeebe, monkeypatch):
    # async def _dummy_run_process(self, process_id, *args, **kwargs):
    #     return None
    monkeypatch.setattr(pyzeebe, "ZeebeClient", lambda *args, **kwargs: create_dummy_client())

    channel = pyzeebe.create_insecure_channel("localhost:1")
    client = pyzeebe.ZeebeClient(channel)

    await client.run_process("process_123")