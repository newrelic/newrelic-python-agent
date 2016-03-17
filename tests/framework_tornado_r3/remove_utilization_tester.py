import sys
import os

# This test script can be run manually, but is also a part of the automated
# tests in this directory.

def remove_utilization_tester(now=True, queue=None):

    # If this function was launched as a subprocess (e.g. using
    # multiprocessing), we need to clear out all newrelic and tornado packages
    # that were copied over from the parent process.

    to_remove = [x for x in sys.modules
            if x.startswith('newrelic') or x.startswith('tornado')]
    for module in to_remove:
        sys.modules.pop(module)
        del module

    import newrelic.agent
    from newrelic.core.agent import agent_instance, Agent
    from newrelic.core.thread_utilization import _utilization_trackers

    config_file = os.path.join(os.path.abspath(os.path.dirname(__file__)),
            'remove_utilization.ini')
    newrelic.agent.initialize(config_file)

    try:
        if now:

            newrelic.agent.register_application(timeout=10)

            # When we register the application first, we have an opportunity to
            # check that thread utilization is, in fact, added to _data_sources,
            # before tornado is imported and removes it.

            # We assert that the Agent instance has been created by reading
            # the private _instance variable, since calling agent_instance()
            # will actually create a new instance if one didn't already exist,
            # which would make this assert pointless.

            assert Agent._instance
            agent = agent_instance()
            source_names = [s[0].__name__ for s in agent._data_sources[None]]
            assert 'thread_utilization_data_source' in source_names

            import tornado.ioloop

        else:

            # In this case, the thread utilization will be removed immediately
            # following registration

            import tornado.ioloop
            assert Agent._instance is None
            newrelic.agent.register_application(timeout=10)

        agent = agent_instance()

        source_names = [s[0].__name__ for s in agent._data_sources[None]]
        assert 'thread_utilization_data_source' not in source_names

        for app in agent._applications.values():
            sampler_names = [x.name for x in app._data_samplers]
            assert 'Thread Utilization' not in sampler_names

        assert len(_utilization_trackers) == 0
    except:
        if queue:
            queue.put(sys.exc_info()[1])
        raise

    if queue:
        queue.put('PASS')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'later':
        passed = remove_utilization_tester(False)
    else:
        passed = remove_utilization_tester(True)

    print("PASSED!")