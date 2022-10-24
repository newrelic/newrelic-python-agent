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

import sys


def get_package_version(name):
    # importlib was introduced into the standard library starting in Python3.8.
    if "importlib" in sys.modules and hasattr(sys.modules["importlib"], "metadata"):
        return sys.modules["importlib"].metadata.version(name)  # pylint: disable=E1101
    elif "pkg_resources" in sys.modules:
        return sys.modules["pkg_resources"].get_distribution(name).version
