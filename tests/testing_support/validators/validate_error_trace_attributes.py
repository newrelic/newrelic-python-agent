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

from newrelic.common.object_wrapper import transient_function_wrapper, function_wrapper


def validate_error_trace_attributes(err_name, required_params=None, forgone_params=None, exact_attrs=None):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    target_error = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_error_trace_attributes(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except Exception:
            raise
        else:
            target_error.append(next((e for e in instance.error_data() if e.type == err_name), None))

        return result

    @function_wrapper
    def _validator_wrapper(wrapped, instance, args, kwargs):
        result = _validate_error_trace_attributes(wrapped)(*args, **kwargs)

        assert target_error and target_error[0] is not None, "No error found with name %s" % err_name
        check_error_attributes(target_error[0].parameters, required_params, forgone_params, exact_attrs)

        return result

    return _validator_wrapper
