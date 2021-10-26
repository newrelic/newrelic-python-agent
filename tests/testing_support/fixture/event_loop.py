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

import pytest

from newrelic.packages import six

# Guard against Python 2 crashes
if six.PY2:
    event_loop = None
else:

    @pytest.fixture(scope="session")
    def event_loop():
        from asyncio import new_event_loop, set_event_loop

        loop = new_event_loop()
        set_event_loop(loop)
        yield loop
