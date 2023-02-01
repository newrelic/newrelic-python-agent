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

try:
    from inspect import signature

    def bind_arguments(func, *args, **kwargs):
        args = signature(func).bind(*args, **kwargs)
        args.apply_defaults()
        return args.arguments

except ImportError:
    from inspect import getcallargs

    def bind_arguments(func, *args, **kwargs):
        try:
            return getcallargs(func, *args, **kwargs)
        except TypeError:
            if hasattr(func, "__call__"):
                return getcallargs(func.__call__, *args, **kwargs)
