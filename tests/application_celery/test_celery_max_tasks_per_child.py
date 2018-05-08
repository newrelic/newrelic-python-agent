from billiard.pool import Worker, os
from billiard.queues import SimpleQueue

from testing_support.validators.validate_function_called import (
        validate_function_called)


@validate_function_called('newrelic.core.agent', 'Agent.shutdown_agent')
def test_max_tasks_per_child():

    os_exit_called = []

    def os_exit(exitcode):
        os_exit_called.append(exitcode)

    orig_exit = os._exit
    os._exit = os_exit

    try:
        worker = Worker(SimpleQueue(), SimpleQueue(), None,
                maxtasks=1)
        worker._do_exit(None, 0)
        assert os_exit_called
    finally:
        os._exit = orig_exit
