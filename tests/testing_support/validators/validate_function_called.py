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


def validate_function_called(module, name):
    """Verify that a function is called."""

    called = []

    @transient_function_wrapper(module, name)
    def _validate_function_called(wrapped, instance, args, kwargs):
        called.append(True)
        return wrapped(*args, **kwargs)

    @function_wrapper
    def wrapper(wrapped, instance, args, kwargs):
        new_wrapper = _validate_function_called(wrapped)
        result = new_wrapper(*args, **kwargs)
        assert called
        return result

    return wrapper
