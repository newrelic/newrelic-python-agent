import pytest

from billiard.pool import Worker
from billiard.queues import SimpleQueue

from testing_support.validators.validate_function_called import (
        validate_function_called)


class OnExit(Exception):
    pass


@validate_function_called('newrelic.core.agent', 'Agent.shutdown_agent')
def test_max_tasks_per_child():

    def on_exit(*args, **kwargs):
        raise OnExit()

    worker = Worker(SimpleQueue(), SimpleQueue(), None,
            maxtasks=1, on_exit=on_exit)
    with pytest.raises(OnExit):
        worker._do_exit(None, 0)
