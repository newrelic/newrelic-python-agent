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

from newrelic.api.application import application_instance
from newrelic.core.agent import agent_instance


# Even though `django_collector_agent_registration_fixture()` also
# has the application deletion during the breakdown of the fixture,
# and `django_collector_agent_registration_fixture()` is scoped to
# "function", not all modules are using this.  Some are using
# `collector_agent_registration_fixture()` scoped to "module".
# Therefore, for those instances, we need to make sure that the
# application is removed from the agent.
@pytest.fixture(scope="module", autouse=True)
def remove_application_from_agent():
    yield
    application = application_instance()
    if application and application.name and (application.name in agent_instance()._applications):
        del agent_instance()._applications[application.name]
