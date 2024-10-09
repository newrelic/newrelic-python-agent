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

from newrelic.api.background_task import background_task
from newrelic.api.llm_custom_attributes import WithLlmCustomAttributes
from newrelic.api.transaction import current_transaction


@background_task()
def test_llm_custom_attributes():
    transaction = current_transaction()
    with WithLlmCustomAttributes({"test": "attr", "test1": "attr1"}):
        assert transaction._llm_context_attrs == {"llm.test": "attr", "llm.test1": "attr1"}

    assert not hasattr(transaction, "_llm_context_attrs")


@pytest.mark.parametrize("context_attrs", (None, "not-a-dict"))
@background_task()
def test_llm_custom_attributes_no_attrs(context_attrs):
    transaction = current_transaction()

    with pytest.raises(TypeError):
        with WithLlmCustomAttributes(context_attrs):
            pass

    assert not hasattr(transaction, "_llm_context_attrs")


@background_task()
def test_llm_custom_attributes_prefixed_attrs():
    transaction = current_transaction()
    with WithLlmCustomAttributes({"llm.test": "attr", "test1": "attr1"}):
        # Validate API does not prefix attributes that already begin with "llm."
        assert transaction._llm_context_attrs == {"llm.test": "attr", "llm.test1": "attr1"}

    assert not hasattr(transaction, "_llm_context_attrs")
