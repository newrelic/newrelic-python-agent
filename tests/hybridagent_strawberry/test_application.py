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
from hybridagent_graphql.test_application import *  # noqa: F403

from newrelic.common.package_version_utils import get_package_version

STRAWBERRY_VERSION = get_package_version("strawberry-graphql")


@pytest.fixture(scope="session", params=["sync-sync", "async-sync", "async-async", "asgi-sync", "asgi-async"])
def target_application(request):
    from ._target_application import target_application

    target_application = target_application[request.param]

    is_asgi = "asgi" if "asgi" in request.param else False
    schema_type = request.param.split("-")[1]

    assert STRAWBERRY_VERSION is not None
    return "Strawberry", target_application, is_asgi, schema_type


# NOTE: Opentelemetry does not capture the field name, so the
# `capture_introspection_setting` is a no-op
