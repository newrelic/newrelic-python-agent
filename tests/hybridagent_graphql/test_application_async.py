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

from inspect import isawaitable


# Async Functions not allowed in Py2
async def example_middleware_async(next, root, info, **args):  # noqa: A002
    return_value = next(root, info, **args)
    if isawaitable(return_value):
        return await return_value
    return return_value


async def error_middleware_async(next, root, info, **args):  # noqa: A002
    raise RuntimeError("Runtime Error!")
