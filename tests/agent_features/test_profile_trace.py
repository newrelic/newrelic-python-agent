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


from testing_support.validators.validate_transaction_metrics import (
    validate_transaction_metrics,
)

from newrelic.api.background_task import background_task
from newrelic.api.profile_trace import ProfileTraceWrapper, profile_trace


def test_profile_trace_wrapper():
    def _test():
        def nested_fn():
            pass

        nested_fn()

    wrapped_test = ProfileTraceWrapper(_test)
    wrapped_test()


@validate_transaction_metrics("test_profile_trace:test_profile_trace_empty_args", background_task=True)
@background_task()
def test_profile_trace_empty_args():
    @profile_trace()
    def _test():
        pass

    _test()


_test_profile_trace_defined_args_scoped_metrics = [("Custom/TestTrace", 1)]


@validate_transaction_metrics(
    "test_profile_trace:test_profile_trace_defined_args",
    scoped_metrics=_test_profile_trace_defined_args_scoped_metrics,
    background_task=True,
)
@background_task()
def test_profile_trace_defined_args():
    @profile_trace(name="TestTrace", group="Custom", label="Label", params={"key": "value"}, depth=7)
    def _test():
        pass

    _test()


_test_profile_trace_callable_args_scoped_metrics = [("Function/TestProfileTrace", 1)]


@validate_transaction_metrics(
    "test_profile_trace:test_profile_trace_callable_args",
    scoped_metrics=_test_profile_trace_callable_args_scoped_metrics,
    background_task=True,
)
@background_task()
def test_profile_trace_callable_args():
    def name_callable():
        return "TestProfileTrace"

    def group_callable():
        return "Function"

    def label_callable():
        return "HSM"

    def params_callable():
        return {"account_id": "12345"}

    @profile_trace(name=name_callable, group=group_callable, label=label_callable, params=params_callable, depth=0)
    def _test():
        pass

    _test()
