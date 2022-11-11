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


from newrelic.common.object_wrapper import function_wrapper
from testing_support.fixtures import core_application_stats_engine

def validate_application_errors(errors=None, required_params=None, forgone_params=None):
    errors = errors or []
    required_params = required_params or []
    forgone_params = forgone_params or []

    @function_wrapper
    def _validate_application_errors(wrapped, instace, args, kwargs):

        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:

            stats = core_application_stats_engine()

            app_errors = stats.error_data()

            expected = sorted(errors)
            captured = sorted([(e.type, e.message) for e in stats.error_data()])

            assert expected == captured, "expected=%r, captured=%r, errors=%r" % (expected, captured, app_errors)

            for e in app_errors:
                for name, value in required_params:
                    assert name in e.parameters["userAttributes"], "name=%r, params=%r" % (name, e.parameters)
                    assert e.parameters["userAttributes"][name] == value, "name=%r, value=%r, params=%r" % (
                        name,
                        value,
                        e.parameters,
                    )

                for name, value in forgone_params:
                    assert name not in e.parameters["userAttributes"], "name=%r, params=%r" % (name, e.parameters)

        return result

    return _validate_application_errors
