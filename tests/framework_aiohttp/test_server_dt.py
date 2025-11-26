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

import json

import pytest
from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

test_uris = [
    ("/error?hello=world", "_target_application:error"),
    ("/coro?hello=world", "_target_application:index"),
    ("/class?hello=world", "_target_application:HelloWorldView._respond"),
]

account_id = "33"
primary_application_id = "2827902"

inbound_payload = {
    "v": [0, 1],
    "d": {
        "ac": account_id,
        "ap": primary_application_id,
        "id": "7d3efb1b173fecfa",
        "tx": "e8b91a159289ff74",
        "pr": 1.234567,
        "sa": True,
        "ti": 1518469636035,
        "tr": "d6b4ba0c3a712ca",
        "ty": "App",
    },
}

expected_attributes = {
    "agent": [],
    "user": [],
    "intrinsic": {
        "traceId": "d6b4ba0c3a712ca",
        "priority": 1.234567,
        "sampled": True,
        "parent.type": "App",
        "parent.app": primary_application_id,
        "parent.account": account_id,
        "parent.transportType": "HTTP",
        "parentId": "e8b91a159289ff74",
        "parentSpanId": "7d3efb1b173fecfa",
    },
}


@pytest.mark.parametrize("uri,txn_name", test_uris)
@override_application_settings(
    {
        "account_id": "33",
        "trusted_account_key": "33",
        "primary_application_id": primary_application_id,
        "distributed_tracing.enabled": True,
    }
)
def test_distributed_tracing_headers(uri, txn_name, aiohttp_app):
    @validate_transaction_metrics(txn_name)
    @validate_transaction_event_attributes(expected_attributes)
    def _test():
        async def fetch():
            headers = {"newrelic": json.dumps(inbound_payload)}
            resp = await aiohttp_app.client.request("GET", uri, headers=headers)

            # DT does not send a response in the headers
            assert "newrelic" not in resp.headers

        aiohttp_app.loop.run_until_complete(fetch())

    _test()
