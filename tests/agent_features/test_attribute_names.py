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
from testing_support.validators.validate_custom_parameters import validate_custom_parameters

from newrelic.api.background_task import background_task
from newrelic.api.transaction import add_custom_attribute, add_custom_attributes
from newrelic.common.encoding_utils import json_decode, json_encode
from newrelic.core.custom_event import create_custom_event


@pytest.mark.parametrize("bulk", (False, True), ids=("single", "bulk"))
@validate_custom_parameters([("valid", "value")], [(b"invalid", "discard")])
@background_task()
def test_byte_attribute_names_are_rejected(bulk):
    if bulk:
        result = add_custom_attributes([(b"invalid", "discard"), ("valid", "value")])
    else:
        assert add_custom_attribute("valid", "value")
        result = add_custom_attribute(b"invalid", "discard")

    assert result is False


@pytest.mark.parametrize("is_ml_event", (False, True))
def test_byte_attribute_names_do_not_break_event_serialization(is_ml_event):
    event = create_custom_event("CustomEvent", {b"invalid": "discard", "valid": b"value"}, is_ml_event=is_ml_event)

    assert event[1] == {"valid": b"value"}
    assert json_decode(json_encode(event))[1] == {"valid": "value"}
