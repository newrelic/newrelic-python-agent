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

import logging

import pytest
from testing_support.fixtures import dt_enabled
from testing_support.validators.validate_span_events import validate_span_events
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

_exact_intrinsics = {"type": "Span"}
_exact_root_intrinsics = _exact_intrinsics.copy().update({"nr.entryPoint": True})
_expected_intrinsics = [
    "traceId",
    "transactionId",
    "sampled",
    "priority",
    "timestamp",
    "duration",
    "name",
    "category",
    "guid",
]
_expected_root_intrinsics = [*_expected_intrinsics, "transaction.name"]
_expected_child_intrinsics = [*_expected_intrinsics, "parentId"]
_unexpected_root_intrinsics = ["parentId"]
_unexpected_child_intrinsics = ["nr.entryPoint", "transaction.name"]

_test_application_rollup_metrics = [
    ("Supportability/DistributedTrace/CreatePayload/Success", 1),
    ("Supportability/TraceContext/Create/Success", 1),
    ("HttpDispatcher", 1),
    ("WebTransaction", 1),
    ("WebTransactionTotalTime", 1),
]


@pytest.mark.parametrize("endpoint", ("/sync", "/async"))
def test_application(caplog, app, endpoint):
    caplog.set_level(logging.ERROR)
    transaction_name = f"GET {endpoint}"

    @dt_enabled
    @validate_span_events(
        exact_intrinsics=_exact_root_intrinsics,
        expected_intrinsics=_expected_root_intrinsics,
        unexpected_intrinsics=_unexpected_root_intrinsics,
    )
    @validate_span_events(
        count=2,  # "asgi.event.type": "http.response.start" and "http.response.body"
        exact_intrinsics=_exact_intrinsics,
        expected_intrinsics=_expected_child_intrinsics,
        unexpected_intrinsics=_unexpected_child_intrinsics,
    )
    @validate_transaction_metrics(
        transaction_name,
        scoped_metrics=[(f"Function/{transaction_name} http send", 2)],
        rollup_metrics=[(f"Function/{transaction_name} http send", 2), *_test_application_rollup_metrics],
    )
    def _test():
        response = app.get(endpoint)
        assert response.status == 200

        # Catch context propagation error messages
        assert not caplog.records

    _test()
