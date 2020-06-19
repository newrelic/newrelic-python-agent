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

from newrelic.core.environment import environment_settings


def test_plugin_list():
    # Let's pretend we fired an import hook
    import newrelic.hooks.adapter_gunicorn

    environment_info = environment_settings()

    for key, plugin_list in environment_info:
        if key == 'Plugin List':
            break
    else:
        assert False, "'Plugin List' not found"

    # Check that bogus plugins don't get reported
    assert 'newrelic.hooks.newrelic' not in plugin_list
