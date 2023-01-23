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


from testing_support.fixtures import check_error_attributes

from newrelic.common.object_wrapper import transient_function_wrapper


def validate_transaction_error_trace_attributes(required_params=None, forgone_params=None, exact_attrs=None):
    """Check the error trace for attributes, expect only one error to be
    present in the transaction.
    """
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_transaction_error_trace(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            error_data = instance.error_data()

            # there should be only one error
            assert len(error_data) == 1
            traced_error = error_data[0]

            check_error_attributes(
                traced_error.parameters, required_params, forgone_params, exact_attrs, is_transaction=True
            )

        return result

    return _validate_transaction_error_trace
