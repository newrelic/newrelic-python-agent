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
import six
from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    code_coverage_fixture,
    collector_agent_registration_fixture,
    collector_available_fixture,
)

_coverage_source = [
    "newrelic.hooks.framework_graphql",
]

code_coverage = code_coverage_fixture(source=_coverage_source)

_default_settings = {
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_ariadne)",
    default_settings=_default_settings,
)


@pytest.fixture(scope="session")
def app():
    from _target_application import _target_application

    return _target_application


if six.PY2:
    collect_ignore = ["test_application_async.py"]
