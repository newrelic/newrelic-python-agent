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
from newrelic.core.application import Application
from newrelic.core.config import global_settings
from newrelic.network.exceptions import ForceAgentDisconnect

from testing_support.fixtures import (
    override_generic_settings,
    failing_endpoint
)
from testing_support.validators.validate_internal_metrics import validate_internal_metrics


SETTINGS = global_settings()


@override_generic_settings(SETTINGS, {
    'developer_mode': True,
})
@failing_endpoint('preconnect', raises=ForceAgentDisconnect)
def test_http_gone_stops_connect():
    app = Application('Python Agent Test (agent_unittests-connect)')
    app.connect_to_data_collector(None)

    # The agent must not reattempt a connection after a ForceAgentDisconnect.
    # If it does, we'll end up with a session here.
    assert not app._active_session


_logging_settings_matrix = [
    (True, True),
    (True, False),
    (False, True),
    (False, False),
]


@override_generic_settings(SETTINGS, {
    'developer_mode': True,
})
@pytest.mark.parametrize("feature_setting,subfeature_setting", _logging_settings_matrix)
def test_logging_connect_supportability_metrics(feature_setting, subfeature_setting):
    metric_value = "enabled" if feature_setting and subfeature_setting else "disabled"

    @override_generic_settings(SETTINGS, {
        "application_logging.enabled": feature_setting,
        "application_logging.forwarding.enabled": subfeature_setting,
        "application_logging.metrics.enabled": subfeature_setting,
        "application_logging.local_decorating.enabled": subfeature_setting,
    })
    @validate_internal_metrics([
        ("Supportability/Logging/Forwarding/Python/%s" % metric_value, 1),
        ("Supportability/Logging/LocalDecorating/Python/%s" % metric_value, 1),
        ("Supportability/Logging/Metrics/Python/%s" % metric_value, 1),
    ])
    def test():
        app = Application('Python Agent Test (agent_unittests-connect)')
        app.connect_to_data_collector(None)

        assert app._active_session
    
    test()
