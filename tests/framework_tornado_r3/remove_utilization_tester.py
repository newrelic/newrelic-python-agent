import sys

import newrelic.agent
from newrelic.core.agent import agent_instance
from newrelic.core.thread_utilization import _utilization_trackers

# This test script is intended to be ran manually. This is because it deals with
# code that can run a couple different ways for agent initialization/
# registration, and the test code deals with this already by the time you get to
# a test case.

def remove_utilization_tester(now=True):

    newrelic.agent.initialize('newrelic.ini')

    if now:
        newrelic.agent.register_application(timeout=10)
        import tornado.httpserver
    else:
        import tornado.httpserver
        newrelic.agent.register_application(timeout=10)

    agent = agent_instance()

    source_names = [s[0].__name__ for s in agent._data_sources[None]]
    assert 'thread_utilization_data_source' not in source_names

    for app in agent._applications.values():
        sampler_names = [x.name for x in app._data_samplers]
        assert 'Thread Utilization' not in sampler_names

    assert len(_utilization_trackers) == 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'later':
        passed = remove_utilization_tester(False)
    else:
        passed = remove_utilization_tester(True)

    print("PASSED!")