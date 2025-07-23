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

from _target_application import add

from newrelic.common.object_wrapper import _NRBoundFunctionWrapper


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
