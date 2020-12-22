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
import pytest
import pika

pika_version_info = tuple(int(num) for num in pika.__version__.split('.')[:2])

new_pika_xfail = pytest.mark.xfail(
        condition=pika_version_info[0] > 0, strict=True,
        reason='test fails if pika version is 1.x or greater')
new_pika_xfail_py37 = pytest.mark.xfail(
        condition=pika_version_info[0] > 0 and sys.version_info >= (3, 7),
        strict=True,
        reason='test fails if pika version is 1.x or greater')
new_pika_skip = pytest.mark.skipif(
        condition=pika_version_info[0] > 0,
        reason='test hangs if pika version is 1.x or greater')
