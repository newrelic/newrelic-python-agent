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

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


@validate_transaction_event_attributes(
    required_params={"agent": (), "user": (), "intrinsic": ()},
    forgone_params={"agent": (), "user": (), "intrinsic": ()},
    exact_attrs={
        "agent": {"response.status": "200", "response.headers.contentType": "text/html; charset=UTF-8"},
        "user": {},
        "intrinsic": {},
    },
)
@override_application_settings(
    {"account_id": 1, "trusted_account_key": 1, "primary_application_id": 1, "distributed_tracing.enabled": True}
)
@validate_transaction_metrics(
    "_target_application:SimpleHandler.get",
    rollup_metrics=(("Supportability/DistributedTrace/AcceptPayload/Success", 1),),
)
def test_inbound_dt(app):
    PAYLOAD = {
        "v": [0, 1],
        "d": {
            "ac": 1,
            "ap": 1,
            "id": "7d3efb1b173fecfa",
            "tx": "e8b91a159289ff74",
            "pr": 1.234567,
            "sa": True,
            "ti": 1518469636035,
            "tr": "d6b4ba0c3a712ca",
            "ty": "App",
        },
    }
    headers = {"newrelic": json.dumps(PAYLOAD)}
    response = app.fetch("/simple", headers=headers)
    assert response.code == 200
