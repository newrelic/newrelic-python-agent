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

import platform

import pytest
from flask import __version__ as flask_version  # required for python 3.7 in lieu of get_package_version_tuple

from newrelic.common.package_version_utils import get_package_version_tuple

try:
    FLASK_VERSION = tuple(int(v) for v in flask_version.split("."))
except:
    # This does not work for Python 3.7 for v2.2.5
    # This only works for flaskmaster
    FLASK_VERSION = get_package_version_tuple("flask")

from testing_support.fixtures import collector_agent_registration_fixture, collector_available_fixture

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_autorum_middleware": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_flask)", default_settings=_default_settings
)


is_flask_v2 = FLASK_VERSION[0] >= 2
is_not_flask_v2_3 = FLASK_VERSION < (2, 3, 0)
is_pypy = platform.python_implementation() == "PyPy"
async_handler_support = is_flask_v2 and not is_pypy
skip_if_not_async_handler_support = pytest.mark.skipif(
    not async_handler_support, reason="Requires async handler support. (Flask >=v2.0.0, CPython)"
)
