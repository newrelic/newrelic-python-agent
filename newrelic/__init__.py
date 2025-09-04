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
    from newrelic._version import __version__, __version_tuple__, version, version_tuple
except ImportError:  # pragma: no cover
    __version__ = version = "0.0.0"  # pragma: no cover
    __version_tuple__ = version_tuple = (0, 0, 0)  # pragma: no cover

# Older compatibility attribute
version_info = version_tuple
