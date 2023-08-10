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

from testing_support.fixtures import core_application_stats_engine

from newrelic.common.object_wrapper import function_wrapper


def validate_application_error_trace_count(num_errors):
    """Validate error event data for a single error occurring outside of a
    transaction.
    """

    @function_wrapper
    def _validate_application_error_trace_count(wrapped, instace, args, kwargs):

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            stats = core_application_stats_engine(None)
            assert len(stats.error_data()) == num_errors

        return result

    return _validate_application_error_trace_count
