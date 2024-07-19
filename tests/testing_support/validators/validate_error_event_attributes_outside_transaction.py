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

from testing_support.fixtures import check_event_attributes

from newrelic.common.object_wrapper import transient_function_wrapper


def validate_error_event_attributes_outside_transaction(
    required_params=None, forgone_params=None, exact_attrs=None, num_errors=None
):
    required_params = required_params or {}
    forgone_params = forgone_params or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.notice_error")
    def _validate_error_event_attributes_outside_transaction(wrapped, instance, args, kwargs):

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise

        event_data = list(instance.error_events)

        if num_errors is not None:
            exc_message = "Expected: %d, Got: %d. Verify StatsEngine is being reset before using this validator." % (
                num_errors,
                len(event_data),
            )
            assert num_errors == len(event_data), exc_message

        for event in event_data:
            check_event_attributes([event], required_params, forgone_params, exact_attrs=exact_attrs)

        return result

    return _validate_error_event_attributes_outside_transaction
