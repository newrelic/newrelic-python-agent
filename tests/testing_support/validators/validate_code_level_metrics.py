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

from testing_support.validators.validate_span_events import validate_span_events
from testing_support.fixtures import dt_enabled
from newrelic.common.object_wrapper import function_wrapper

def validate_code_level_metrics(namespace, function, builtin=False, count=1, index=-1):
    """Verify that code level metrics are generated for a callable."""

    if builtin:
        validator = validate_span_events(
            exact_agents={"code.function": function, "code.namespace": namespace, "code.filepath": "<builtin>"},
            unexpected_agents=["code.lineno"],
            count=count,
            index=index,
        )
    else:
        validator = validate_span_events(
            exact_agents={"code.function": function, "code.namespace": namespace},
            expected_agents=["code.lineno", "code.filepath"],
            count=count,
            index=index,
        )

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        validator(dt_enabled(wrapped))(*args, **kwargs)

    return wrapper

