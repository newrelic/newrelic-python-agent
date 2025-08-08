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

from _target_application import add, add_with_super
from celery.app.trace import setup_worker_optimizations, reset_worker_optimizations

from newrelic.common.object_wrapper import _NRBoundFunctionWrapper

def test_worker_optimizations_preserve_instrumentation(celery_worker_available):
    """
    Tests that worker optimizations do not remove New Relic instrumentation.
    
    Previously, New Relic was applying instrumentation hooks to `Task`/`BaseTask`.
    Setting up and resetting worker optimizations were removing the instrumentation
    so, instrumentation was created to remove the instrumentation, run the worker
    optimizations, and then reapply the instrumentation.

    The purpose of the worker optimizations is to circumvent an issue where a
    custom task class defines `__call__` and also calls `super().__call__`.

    We can ensure that the instrumentation is preserved for the `add_with_super` task.
    """
    is_instrumented = lambda: isinstance(add_with_super.__call__, _NRBoundFunctionWrapper)

    reset_worker_optimizations()
    assert is_instrumented(), "Instrumentation not initially applied."

    setup_worker_optimizations(celery_worker_available.app)
    assert is_instrumented(), "setup_worker_optimizations removed instrumentation."

    reset_worker_optimizations()
    assert is_instrumented(), "reset_worker_optimizations removed instrumentation."
    

def test_task_wrapping_detection():
    """
    Ensure celery detects our monkeypatching properly and will run our instrumentation
    on __call__ and runs that instead of micro-optimizing it away to a run() call.

    If this is not working, most other tests in this file will fail as the different ways
    of running celery tasks will not all run our instrumentation.
    """
    assert isinstance(add.__call__, _NRBoundFunctionWrapper), (
        "Celery task add.__call__ is not wrapped by New Relic instrumentation. "
        "This indicates that the monkeypatching of celery has not been applied correctly."
    )
