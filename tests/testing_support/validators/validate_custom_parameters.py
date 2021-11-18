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
from testing_support.fixtures import catch_background_exceptions


def validate_custom_parameters(required_params=None, forgone_params=None):
    required_params = required_params or []
    forgone_params = forgone_params or []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    @catch_background_exceptions
    def _validate_custom_parameters(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        # these are pre-destination applied attributes, so they may not
        # actually end up in a transaction/error trace, we are merely testing
        # for presence on the TransactionNode

        attrs = {}
        for attr in transaction.user_attributes:
            attrs[attr.name] = attr.value

        for name, value in required_params:
            assert name in attrs, "name=%r, params=%r" % (name, attrs)
            assert attrs[name] == value, "name=%r, value=%r, params=%r" % (name, value, attrs)

        for name, value in forgone_params:
            assert name not in attrs, "name=%r, params=%r" % (name, attrs)

        return wrapped(*args, **kwargs)

    return _validate_custom_parameters