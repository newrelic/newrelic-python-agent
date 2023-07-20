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


from newrelic.common.object_wrapper import (
    function_wrapper,
    transient_function_wrapper,
)
from testing_support.fixtures import check_event_attributes

def validate_transaction_event_attributes(required_params=None, forgone_params=None, exact_attrs=None, index=-1):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    captured_events = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _capture_transaction_events(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            event_data = instance.transaction_events
            captured_events.append(event_data)
            return result

    @function_wrapper
    def _validate_transaction_event_attributes(wrapped, instance, args, kwargs):
        _new_wrapper = _capture_transaction_events(wrapped)
        result = _new_wrapper(*args, **kwargs)

        assert captured_events, "No events captured"
        event_data = captured_events[index]
        captured_events[:] = []

        check_event_attributes(event_data, required_params, forgone_params, exact_attrs)

        return result

    return _validate_transaction_event_attributes