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

import copy

from newrelic.common.object_wrapper import (
    function_wrapper,
    transient_function_wrapper,
)
from testing_support.fixtures import catch_background_exceptions

def validate_transaction_errors(errors=None, required_params=None, forgone_params=None):
    errors = errors or []
    required_params = required_params or []
    forgone_params = forgone_params or []
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

        assert expected == compare_to, "expected=%r, captured=%r, errors=%r" % (expected, compare_to, captured)

        for e in captured:
            assert e.span_id
            for name, value in required_params:
                assert name in e.custom_params, "name=%r, params=%r" % (name, e.custom_params)
                assert e.custom_params[name] == value, "name=%r, value=%r, params=%r" % (
                    name,
                    value,
                    e.custom_params,
                )

            for name, value in forgone_params:
                assert name not in e.custom_params, "name=%r, params=%r" % (name, e.custom_params)

        return output

    return _validate_transaction_errors
