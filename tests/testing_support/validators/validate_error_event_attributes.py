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

from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper


def validate_error_event_attributes(required_params=None, forgone_params=None, exact_attrs=None):
    """Check the error event for attributes, expect only one error to be
    present in the transaction.
    """
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}
    error_data_samples = []

    @function_wrapper
    def _validate_wrapper(wrapped, instance, args, kwargs):
        @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
        def _validate_error_event_attributes(wrapped, instance, args, kwargs):
            try:
                result = wrapped(*args, **kwargs)
            except:
                raise

            event_data = instance.error_events
            for sample in event_data:
                error_data_samples.append(sample)

            check_event_attributes(event_data, required_params, forgone_params, exact_attrs)

            return result

        _new_wrapper = _validate_error_event_attributes(wrapped)
        val = _new_wrapper(*args, **kwargs)
        assert error_data_samples
        return val

    return _validate_wrapper
