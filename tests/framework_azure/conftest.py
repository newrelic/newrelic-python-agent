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

# import os

from testing_support.fixtures import (  # noqa: F401; pylint: disable=W0611
    collector_agent_registration_fixture,
    collector_available_fixture,
)

# testing_environment_variables = {
#     "FUNCTIONS_WORKER_RUNTIME": "Python",
#     "PYTHON_ENABLE_WORKER_EXTENSIONS": "True",
#     "WEBSITE_SITE_NAME": "azure-functions-test-app",
#     "WEBSITE_OWNER_NAME": "b999997b-cb91-49e0-b922-c9188372bdba+testing-rg-EastUS2webspace-Linux",
#     "REGION_NAME": "East US 2",
# }

# os.environ.update(testing_environment_variables)

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "host": "staging-collector.newrelic.com",
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_azure)", default_settings=_default_settings
)
