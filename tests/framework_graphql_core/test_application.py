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

from newrelic.core.config import global_settings

from testing_support.fixtures import validate_transaction_metrics


_test_basic_metrics = (
    ('WebTransaction', 1),
    ('WebTransaction/Function/graphql.execution.execute:execute', 1),
    ('WebTransactionTotalTime', 1),
    ('WebTransactionTotalTime/Function/graphql.execution.execute:execute', 1),
)

@validate_transaction_metrics(
    'graphql.execution.execute:execute',
    rollup_metrics=_test_basic_metrics,
)
def test_basic(app):
    from graphql import graphql_sync

    response = graphql_sync(app, '{ hello }')
    assert "Hello!" in str(response.data)
