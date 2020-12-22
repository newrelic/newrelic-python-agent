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
