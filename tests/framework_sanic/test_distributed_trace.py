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

from testing_support.fixtures import override_application_settings
from testing_support.validators.validate_transaction_event_attributes import validate_transaction_event_attributes
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

from newrelic.api.application import application_instance
from newrelic.api.external_trace import ExternalTrace
from newrelic.api.transaction import Transaction

BASE_METRICS = [("Function/_target_application:index", 1)]
DT_METRICS = [
    ("Supportability/DistributedTrace/AcceptPayload/Success", None),
    ("Supportability/TraceContext/TraceParent/Accept/Success", 1),
]
BASE_ATTRS = ["response.status", "response.headers.contentType", "response.headers.contentLength"]


def raw_headers(response):
    try:
        # Manually encode into bytes
        return " ".join(f"{k}: {v}" for k, v in response.processed_headers).encode()
    except AttributeError:
        try:
            return response.get_headers()
        except AttributeError:
            return response.output()


@validate_transaction_metrics(
    "_target_application:index", scoped_metrics=BASE_METRICS, rollup_metrics=BASE_METRICS + DT_METRICS
)
@override_application_settings({"distributed_tracing.enabled": True})
@validate_transaction_event_attributes(required_params={"agent": BASE_ATTRS, "user": [], "intrinsic": []})
def test_inbound_distributed_trace(app):
    transaction = Transaction(application_instance())
    dt_headers = ExternalTrace.generate_request_headers(transaction)

    response = app.fetch("get", "/", headers=dict(dt_headers))
    assert response.status == 200
