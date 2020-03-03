import pytest
from newrelic.core.agent import Agent
from newrelic.core.config import finalize_application_settings
from testing_support.fixtures import override_generic_settings


class FakeApplication(object):
    name = 'Fake'

    def __init__(self, *args, **kwargs):
        self.harvest_flexible = 0
        self.harvest_default = 0
        self.is_alive = True

    def harvest(self, shutdown=False, flexible=False, *args, **kwargs):
        assert self.is_alive

        if flexible:
            self.harvest_flexible += 1
        else:
            self.harvest_default += 1

        if shutdown:
            self.is_alive = False


class FakeAgent(Agent):
    def __init__(self, *args, **kwargs):
        super(FakeAgent, self).__init__(*args, **kwargs)
        self._applications = {'fake': FakeApplication()}


SETTINGS = finalize_application_settings({
    'enabled': True,
    'debug.disable_harvest_until_shutdown': False,
})


@pytest.fixture
def agent():
    agent = FakeAgent(SETTINGS)
    yield agent
    agent.shutdown_agent(timeout=5)
    assert not agent._harvest_thread.is_alive()


_override_settings = {
    'event_harvest_config.report_period_ms': 80.0 * 1000.0,
}


@override_generic_settings(SETTINGS, _override_settings)
def test_agent_final_harvest(agent):
    agent.activate_agent()
    assert agent._harvest_thread.is_alive()

    agent.shutdown_agent(timeout=5)
    assert not agent._harvest_thread.is_alive()

    assert agent._applications['fake'].harvest_flexible == 1
    assert agent._applications['fake'].harvest_default == 1
