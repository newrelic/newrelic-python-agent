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

from testing_support.fixtures import core_application_stats_engine

from newrelic.common.object_wrapper import transient_function_wrapper


def check_attributes(parameters, required_params=None, forgone_params=None, exact_attrs=None):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    intrinsics = parameters.get("intrinsics", {})
    user_attributes = parameters.get("userAttributes", {})
    agent_attributes = parameters.get("agentAttributes", {})

    if required_params:
        for param in required_params["agent"]:
            assert param in agent_attributes, (param, agent_attributes)
        for param in required_params["user"]:
            assert param in user_attributes, (param, user_attributes)
        for param in required_params["intrinsic"]:
            assert param in intrinsics, (param, intrinsics)

    if forgone_params:
        for param in forgone_params["agent"]:
            assert param not in agent_attributes, (param, agent_attributes)
        for param in forgone_params["user"]:
            assert param not in user_attributes, (param, user_attributes)
        for param in forgone_params["intrinsic"]:
            assert param not in intrinsics, (param, intrinsics)

    if exact_attrs:
        for param, value in exact_attrs["agent"].items():
            assert agent_attributes[param] == value, ((param, value), agent_attributes)
        for param, value in exact_attrs["user"].items():
            assert user_attributes[param] == value, ((param, value), user_attributes)
        for param, value in exact_attrs["intrinsic"].items():
            assert intrinsics[param] == value, ((param, value), intrinsics)


def check_error_attributes(
    parameters, required_params=None, forgone_params=None, exact_attrs=None, is_transaction=True
):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    parameter_fields = ["userAttributes"]
    if is_transaction:
        parameter_fields.extend(["stack_trace", "agentAttributes", "intrinsics"])

    for field in parameter_fields:
        assert field in parameters

    # we can remove this after agent attributes transition is all over
    assert "parameter_groups" not in parameters
    assert "custom_params" not in parameters
    assert "request_params" not in parameters
    assert "request_uri" not in parameters

    check_attributes(parameters, required_params, forgone_params, exact_attrs)


def core_application_stats_engine_error(error_type, app_name=None):
    """Return a single error with the type of error_type, or None.

    In the core application StatsEngine, look in StatsEngine.error_data()
    and return the first error with the type of error_type. If none found,
    return None.

    Useful for verifying that application.notice_error() works, since
    the error is saved outside of a transaction. Must use a unique error
    type per test in a single test file, so that it returns the error you
    expect. (If you have 2 tests that record the same type of exception, then
    StatsEngine.error_data() will contain 2 errors with the same type, but
    this function will always return the first one it finds.)

    """

    stats = core_application_stats_engine(app_name)
    errors = stats.error_data()
    return next((e for e in errors if e.type == error_type), None)


def validate_error_trace_attributes_outside_transaction(
    err_name, required_params=None, forgone_params=None, exact_attrs=None
):
    required_params = required_params or {}
    forgone_params = forgone_params or {}
    exact_attrs = exact_attrs or {}

    @transient_function_wrapper("newrelic.core.stats_engine", "StatsEngine.notice_error")
    def _validate_error_trace_attributes_outside_transaction(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            target_error = core_application_stats_engine_error(err_name)

            check_error_attributes(
                target_error.parameters, required_params, forgone_params, exact_attrs, is_transaction=False
            )

        return result

    return _validate_error_trace_attributes_outside_transaction
