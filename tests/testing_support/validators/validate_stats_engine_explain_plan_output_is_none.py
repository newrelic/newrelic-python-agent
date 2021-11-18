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

from newrelic.common.object_wrapper import transient_function_wrapper


def validate_stats_engine_explain_plan_output_is_none():
    """This fixture isn't useful by itself, because you need to generate
    explain plans, which doesn't normally occur during record_transaction().

    Use the `validate_transaction_slow_sql_count` fixture to force the
    generation of slow sql data after record_transaction(), which will run
    newrelic.core.stats_engine.explain_plan.

    """

    @transient_function_wrapper("newrelic.core.stats_engine", "explain_plan")
    def _validate_explain_plan_output_is_none(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            assert result is None

        return result

    return _validate_explain_plan_output_is_none