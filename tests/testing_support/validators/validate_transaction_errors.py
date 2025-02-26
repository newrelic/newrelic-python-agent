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

from newrelic.common.object_wrapper import function_wrapper, transient_function_wrapper
from testing_support.fixtures import catch_background_exceptions


def validate_transaction_errors(errors=None, required_params=None, forgone_params=None, expected_errors=None):
    errors = errors or []
    required_params = required_params or []
    forgone_params = forgone_params or []
    expected_errors = expected_errors or []
    captured_errors = []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    @catch_background_exceptions
    def _capture_transaction_errors(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        captured = transaction.errors

        captured_errors.append(captured)

        return wrapped(*args, **kwargs)

    @function_wrapper
    def _validate_transaction_errors(wrapped, instance, args, kwargs):
        _new_wrapped = _capture_transaction_errors(wrapped)
        output = _new_wrapped(*args, **kwargs)

        expected = sorted(errors)

        if captured_errors:
            captured = captured_errors[0]
        else:
            captured = []

        if errors and isinstance(errors[0], (tuple, list)):
            compare_to = sorted([(e.type, e.message) for e in captured])
        else:
            compare_to = sorted([e.type for e in captured])

        assert expected == compare_to, f"expected={expected!r}, captured={compare_to!r}, errors={captured!r}"

        for e in captured:
            assert e.span_id
            for name, value in required_params:
                assert name in e.custom_params, f"name={name!r}, params={e.custom_params!r}"
                assert e.custom_params[name] == value, f"name={name!r}, value={value!r}, params={e.custom_params!r}"

            for name, value in forgone_params:
                assert name not in e.custom_params, f"name={name!r}, params={e.custom_params!r}"

            if e.type in expected_errors:
                assert e.expected is True
            else:
                assert e.expected is False

        return output

    return _validate_transaction_errors
