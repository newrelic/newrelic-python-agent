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

import celery
from _target_application import add

from newrelic.common.object_wrapper import _NRBoundFunctionWrapper

FORGONE_TASK_METRICS = [("Function/_target_application.add", None), ("Function/_target_application.tsum", None)]


def test_task_wrapping_detection():
    """
    Ensure celery detects our monkeypatching properly and will run our instrumentation
    on __call__ and runs that instead of micro-optimizing it away to a run() call.

    If this is not working, most other tests in this file will fail as the different ways
    of running celery tasks will not all run our instrumentation.
    """
    assert celery.app.trace.task_has_custom(add, "__call__")


def test_worker_optimizations_preserve_instrumentation(celery_worker_available):
    is_instrumented = lambda: isinstance(celery.app.task.BaseTask.__call__, _NRBoundFunctionWrapper)

    celery.app.trace.reset_worker_optimizations()
    assert is_instrumented(), "Instrumentation not initially applied."

    celery.app.trace.setup_worker_optimizations(celery_worker_available.app)
    assert is_instrumented(), "setup_worker_optimizations removed instrumentation."

    celery.app.trace.reset_worker_optimizations()
    assert is_instrumented(), "reset_worker_optimizations removed instrumentation."
