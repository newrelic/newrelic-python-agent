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


def validate_transaction_object_attributes(attributes):
    # This validates attributes on the transaction object that is passed to
    # `StatsEngine.record_transaction`.
    #
    # Args:
    #
    #       attributes: a dictionary of expected attributes (key) and values (value)

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_attributes(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)

        for attr, value in attributes.items():
            assert getattr(transaction, attr) == value

        return wrapped(*args, **kwargs)

    return _validate_attributes
