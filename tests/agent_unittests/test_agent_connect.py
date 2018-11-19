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
    app.connect_to_data_collector()

    # The agent must not reattempt a connection after a ForceAgentDisconnect.
    # If it does, we'll end up with a session here.
    assert not app._active_session
