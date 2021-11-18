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
from testing_support.fixtures import (
    error_user_params_added,
    _validate_event_attributes
)


def validate_error_event_sample_data(required_attrs=None, required_user_attrs=True, num_errors=1):
    """Validate the data collected for error_events. This test depends on values
    in the test application from agent_features/test_analytics.py, and is only
    meant to be run as a validation with those tests.
    """
    required_attrs = required_attrs or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_error_event_sample_data(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            def _bind_params(transaction, *args, **kwargs):
                return transaction

            transaction = _bind_params(*args, **kwargs)

            error_events = transaction.error_events(instance.stats_table)
            assert len(error_events) == num_errors
            for sample in error_events:

                assert isinstance(sample, list)
                assert len(sample) == 3

                intrinsics, user_attributes, _ = sample

                # These intrinsics should always be present

                assert intrinsics["type"] == "TransactionError"
                assert intrinsics["transactionName"] == required_attrs["transactionName"]
                assert intrinsics["error.class"] == required_attrs["error.class"]
                assert intrinsics["error.message"].startswith(required_attrs["error.message"])
                assert intrinsics["error.expected"] == required_attrs["error.expected"]
                assert intrinsics["nr.transactionGuid"] is not None
                assert intrinsics["spanId"] is not None

                # check that transaction event intrinsics haven't bled in

                assert "name" not in intrinsics

                _validate_event_attributes(intrinsics, user_attributes, required_attrs, required_user_attrs)
                if required_user_attrs:
                    error_user_params = error_user_params_added()
                    for param, value in error_user_params.items():
                        assert user_attributes[param] == value

        return result

    return _validate_error_event_sample_data