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

from newrelic.core.application import Application
from newrelic.core.config import global_settings
from newrelic.network.exceptions import ForceAgentDisconnect

from testing_support.fixtures import (override_generic_settings,
        failing_endpoint)


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
