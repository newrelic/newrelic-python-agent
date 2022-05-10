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

from framework_graphql.test_application import *


@pytest.fixture(scope="session", params=["sync-sync", "async-sync", "async-async", "asgi-sync", "asgi-async"])
def target_application(request):
    from ._target_application import target_application
    target_application = target_application[request.param]

    try:
        import strawberry
        version = strawberry.__version__
    except Exception:
        import pkg_resources
        version = pkg_resources.get_distribution("strawberry-graphql").version

    is_asgi = "asgi" in request.param
    schema_type = request.param.split("-")[1]

    assert version is not None
    return "Strawberry", version, target_application, not is_asgi, schema_type, 0

