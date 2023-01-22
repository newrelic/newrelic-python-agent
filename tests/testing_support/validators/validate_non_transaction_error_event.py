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

from time import time

from testing_support.fixtures import core_application_stats_engine

from newrelic.common.object_wrapper import function_wrapper


def validate_non_transaction_error_event(required_intrinsics=None, num_errors=1, required_user=None, forgone_user=None):
    """Validate error event data for a single error occurring outside of a
    transaction.
    """
    required_intrinsics = required_intrinsics or {}
    required_user = required_user or {}
    forgone_user = forgone_user or []

    @function_wrapper
    def _validate_non_transaction_error_event(wrapped, instace, args, kwargs):

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            stats = core_application_stats_engine(None)

            assert stats.error_events.num_seen == num_errors
            for event in stats.error_events:

                assert len(event) == 3  # [intrinsic, user, agent attributes]

                intrinsics = event[0]

                # The following attributes are all required, and also the only
                # intrinsic attributes that can be included in an error event
                # recorded outside of a transaction

                assert intrinsics["type"] == "TransactionError"
                assert intrinsics["transactionName"] is None
                assert intrinsics["error.class"] == required_intrinsics["error.class"]
                assert intrinsics["error.message"].startswith(required_intrinsics["error.message"])
                assert intrinsics["error.expected"] == required_intrinsics["error.expected"]
                now = time()
                assert isinstance(intrinsics["timestamp"], int)
                assert intrinsics["timestamp"] <= 1000.0 * now

                user_params = event[1]
                for name, value in required_user.items():
                    assert name in user_params, "name=%r, params=%r" % (name, user_params)
                    assert user_params[name] == value, "name=%r, value=%r, params=%r" % (name, value, user_params)

                for param in forgone_user:
                    assert param not in user_params

        return result

    return _validate_non_transaction_error_event
