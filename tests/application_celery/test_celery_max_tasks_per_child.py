import pytest

from billiard import get_context
from billiard.pool import Worker

from testing_support.validators.validate_function_called import (
        validate_function_called)


class OnExit(Exception):
    pass


@validate_function_called('newrelic.core.agent', 'Agent.shutdown_agent')
def test_max_tasks_per_child():

    def on_exit(*args, **kwargs):
        raise OnExit()

    ctx = get_context()
    worker = Worker(ctx.SimpleQueue(), ctx.SimpleQueue(), None,
            maxtasks=1, on_exit=on_exit)

    with pytest.raises(OnExit):
        worker._do_exit(None, 0)
