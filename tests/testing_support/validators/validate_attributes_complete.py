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


def validate_attributes_complete(attr_type, required_attrs=None, forgone_attrs=None):

    # This differs from `validate_attributes` in that all fields of
    # Attribute must match (name, value, and destinations), not just
    # name. It's a more thorough test, but it's more of a pain to set
    # up, since you have to pass lists of Attributes to required_attrs
    # and forgone_attrs. For required destinations, the attribute will
    # match if at least the required destinations are present. For
    # forgone attributes the test will fail if any of the destinations
    # provided in the forgone attribute are found.
    #
    # Args:
    #
    #       attr_type: 'intrinsic' or 'agent' or 'user'
    #       required_attrs: List of Attributes that must be present.
    #       forgone_attrs: List of Attributes that must NOT be present.
    #
    # Note:
    #
    # The 'intrinsics' come from `transaction.trace_intrinsics`.

    required_attrs = required_attrs or []
    forgone_attrs = forgone_attrs or []

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.record_transaction")
    def _validate_attributes_complete(wrapped, instance, args, kwargs):
        def _bind_params(transaction, *args, **kwargs):
            return transaction

        transaction = _bind_params(*args, **kwargs)
        attribute_filter = transaction.settings.attribute_filter

        if attr_type == "intrinsic":

            # Intrinsics are stored as a dict, so for consistency's sake
            # in this test, we convert them to Attributes.

            items = transaction.trace_intrinsics
            attributes = create_attributes(items, DST_ERROR_COLLECTOR | DST_TRANSACTION_TRACER, attribute_filter)

        elif attr_type == "agent":
            attributes = transaction.agent_attributes

        elif attr_type == "user":
            attributes = transaction.user_attributes

        def _find_match(a, attributes):
            # Match by name and value. Ignore destination.
            return next((match for match in attributes if match.name == a.name and match.value == a.value), None)

        # Check that there is a name/value match, and that the destinations
        # for the matched attribute include the ones in required.

        for required in required_attrs:
            match = _find_match(required, attributes)
            assert match, "required=%r, attributes=%r" % (required, attributes)

            result_dest = required.destinations & match.destinations
            assert result_dest == required.destinations, "required=%r, attributes=%r" % (required, attributes)

        # Check that the name and value are NOT going to ANY of the
        # destinations provided as forgone, either because there is no
        # name/value match, or because there is a name/value match, but
        # the destinations do not include the ones in forgone.

        for forgone in forgone_attrs:
            match = _find_match(forgone, attributes)

            if match:
                result_dest = forgone.destinations & match.destinations
                assert result_dest == 0, "forgone=%r, attributes=%r" % (forgone, attributes)

        return wrapped(*args, **kwargs)

    return _validate_attributes_complete