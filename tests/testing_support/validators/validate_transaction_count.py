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

from newrelic.common.object_wrapper import (transient_function_wrapper,
        function_wrapper)


def validate_transaction_count(count):
    _transactions = []

    @transient_function_wrapper('newrelic.core.stats_engine',
            'StatsEngine.record_transaction')
    def _increment_count(wrapped, instance, args, kwargs):
        _transactions.append(getattr(args[0], "name", True))
        return wrapped(*args, **kwargs)

    @function_wrapper
    def _validate_transaction_count(wrapped, instance, args, kwargs):
        _new_wrapped = _increment_count(wrapped)
        result = _new_wrapped(*args, **kwargs)
        assert count == len(_transactions), (count, len(_transactions), _transactions)

        return result

    return _validate_transaction_count
