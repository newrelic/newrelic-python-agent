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

import functools

import pytest
from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_azurefunctions)", default_settings=_default_settings
)


@pytest.fixture(scope="session", autouse=True)
def dispatcher():
    """Fixture that starts the worker on a separate thread and returns the dispatcher instance."""
    from .sample_application.worker import start_dispatcher_thread

    # Start the dispatcher thread
    dispatcher_ = start_dispatcher_thread()

    # Return the dispatcher instance for use in tests
    yield dispatcher_

    # Stop worker gracefully
    dispatcher_.stop()


@pytest.fixture(scope="session", params=["sync", "async"])
def is_async(request):
    """Fixture that parametrizes the endpoint type between sync and async."""
    return request.param == "async"


@pytest.fixture(scope="session")
def send_invocation(is_async, dispatcher):
    """Fixture that returns the _send_event interface."""
    from .sample_application.messages import send_invocation_event

    return functools.partial(send_invocation_event, dispatcher, is_async=is_async)
