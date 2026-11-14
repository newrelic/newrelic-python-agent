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

from types import SimpleNamespace

import pytest

from newrelic.common.encoding_utils import json_encode
from newrelic.core import custom_event
from newrelic.core.attribute import MAX_NUM_ML_USER_ATTRIBUTES, MAX_NUM_USER_ATTRIBUTES


@pytest.fixture
def current_timestamp(monkeypatch):
    monkeypatch.setattr(custom_event, "time", SimpleNamespace(time=lambda: 1700000000.0))
    return 1700000000000


@pytest.mark.parametrize("is_ml_event", (False, True))
@pytest.mark.parametrize(
    "timestamp",
    (object(), {"invalid": 1}, [1700000000000], "1700000000000", True, float("nan"), float("inf"), -(2**64), 2**64),
)
def test_invalid_timestamp_does_not_corrupt_event(timestamp, is_ml_event, current_timestamp):
    event = custom_event.create_custom_event(
        "CustomEvent", {"timestamp": timestamp, "orderId": 1}, is_ml_event=is_ml_event
    )

    assert event == [{"type": "CustomEvent", "timestamp": current_timestamp}, {"orderId": 1}]
    json_encode([event], allow_nan=False)


@pytest.mark.parametrize("timestamp", (1700000000, 1700000000000, 1700000000000.5))
def test_numeric_timestamp_is_preserved(timestamp):
    event = custom_event.create_custom_event("CustomEvent", {"timestamp": timestamp})

    assert event == [{"type": "CustomEvent", "timestamp": timestamp}, {"timestamp": timestamp}]


@pytest.mark.parametrize("timestamp", (None, 0))
def test_empty_timestamp_uses_current_time(timestamp, current_timestamp):
    event = custom_event.create_custom_event("CustomEvent", {"timestamp": timestamp})

    assert event[0]["timestamp"] == current_timestamp


@pytest.mark.parametrize("is_ml_event", (False, True))
def test_timestamp_is_preserved_after_attribute_limit(is_ml_event):
    limit = MAX_NUM_ML_USER_ATTRIBUTES if is_ml_event else MAX_NUM_USER_ATTRIBUTES
    params = {f"attr_{index}": index for index in range(limit)}
    params["timestamp"] = 1700000000000

    event = custom_event.create_custom_event("CustomEvent", params, is_ml_event=is_ml_event)

    assert event[0]["timestamp"] == params["timestamp"]
    assert len(event[1]) == limit
    assert "timestamp" not in event[1]
