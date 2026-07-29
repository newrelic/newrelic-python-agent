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

import pytest
from testing_support.fixture.event_loop import event_loop as loop

from ._test_agent import MODEL


@pytest.fixture
def bedrock_client(vcr_recording):
    from agent_framework.amazon import BedrockChatClient

    if vcr_recording:
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if not (access_key and secret_key):
            raise RuntimeError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables required.")
    else:
        access_key = "NOT-A-REAL-SECRET"
        secret_key = "NOT-A-REAL-SECRET"

    return BedrockChatClient(model=MODEL, region="us-east-1", access_key=access_key, secret_key=secret_key)
