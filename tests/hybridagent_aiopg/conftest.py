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

"""
This test suite tests the following scenarios:
1. Hybrid Agent with a framework that is instrumented by OpenTelemetry (aiopg)
but not New Relic.
2. Despite New Relic not having instrumentation support for aiopg, there are
framework  dependencies that are present in this library (psycopg2) that New
Relic does instrument, so this ensures that these hooks are disabled so that
there is no conflict with OpenTelemetry instrumentation.
3. `opentelemetry.traces.enabled` setting is toggled on and off to ensure
that traces are created or not created as expected.
"""


from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "opentelemetry.enabled": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (Hybrid Agent)", default_settings=_default_settings
)

