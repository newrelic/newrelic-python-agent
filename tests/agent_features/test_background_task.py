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

from newrelic.api.application import application_instance
from newrelic.api.background_task import BackgroundTask
from newrelic.api.function_trace import FunctionTrace


def test_nested_context_managers():
    app = application_instance()
    outer = BackgroundTask(app, 'outer')
    inner = BackgroundTask(app, 'inner')
    with outer:
        with inner:
            assert not inner.enabled


def test_sentinel_exited_complete_root_exception():
    """
    This test forces a transaction to exit while it still has an active trace
    this causes an exception to be raised in TraceCache complete_root(). It
    verifies that the sentinel.exited property is set to true if an exception
    is raised in complete_root(), and that the exception is caught.
    """

    txn = None
    sentinel = None
    txn = BackgroundTask(application_instance(), "Parent")
    txn.__enter__()
    sentinel = txn.root_span
    trace = FunctionTrace("trace")
    trace.__enter__()
    txn.__exit__(None, None, None)
    assert sentinel.exited
    # Make sure to exit properly so cleanup is performed
    trace.__exit__(None, None, None)
    txn.__exit__(None, None, None)
