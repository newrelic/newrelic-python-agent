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

import gc
import pytest
import newrelic.packages.six as six

from newrelic.api.background_task import BackgroundTask
from newrelic.api.application import application_instance
from newrelic.common.object_wrapper import transient_function_wrapper, function_wrapper


@function_wrapper
def capture_errors(wrapped, instance, args, kwargs):
    ERRORS = []

    @transient_function_wrapper(
            'newrelic.api.transaction', 'Transaction.__exit__')
    def capture_errors(wrapped, instance, args, kwargs):
        try:
            return wrapped(*args, **kwargs)
        except Exception as e:
            ERRORS.append(e)
            raise

    result = capture_errors(wrapped)(*args, **kwargs)

    assert not ERRORS
    return result


@pytest.mark.parametrize('circular', (True, False))
@capture_errors
def test_dead_transaction_ends(circular):
    if circular and six.PY2:
        pytest.skip("Circular references in py2 result in a memory leak. "
                "There is no way to remove transactions from the weakref "
                "cache in this case.")

    transaction = BackgroundTask(
            application_instance(), "test_dead_transaction_ends")
    if circular:
        transaction._self = transaction

    transaction.__enter__()
    del transaction
    gc.collect()
