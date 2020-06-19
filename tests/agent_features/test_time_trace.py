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

from newrelic.api.transaction import end_of_transaction
from newrelic.api.background_task import background_task
from newrelic.api.function_trace import FunctionTrace


from testing_support.fixtures import validate_transaction_metrics


@validate_transaction_metrics(
    'test_trace_after_end_of_transaction',
    background_task=True,
    scoped_metrics=[('Function/foobar', None)],
)
@background_task(name='test_trace_after_end_of_transaction')
def test_trace_after_end_of_transaction(caplog):
    end_of_transaction()
    with FunctionTrace("foobar"):
        pass

    error_messages = [record for record in caplog.records
            if record.levelno >= logging.ERROR]
    assert not error_messages
