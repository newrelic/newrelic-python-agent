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
from framework_graphql.test_application import *  # noqa


@pytest.fixture(scope="session", params=["wsgi-sync"])
def target_application(request):
    from ._target_application import target_application

    target_application = target_application.get(request.param, None)
    if target_application is None:
        pytest.skip("Unsupported combination.")
        return

    try:
        import graphene_django

        version = graphene_django.__version__
    except Exception:
        import pkg_resources

        version = pkg_resources.get_distribution("graphene_django").version

    param = request.param.split("-")
    is_background = param[0] not in {"wsgi", "asgi"}
    schema_type = param[1]
    extra_spans = 4 if param[0] == "wsgi" else 0

    assert version is not None
    return "GrapheneDjango", version, target_application, is_background, schema_type, extra_spans


# def test_no_harm(target_application):
#     framework, version, target_application, is_bg, schema_type, extra_spans = target_application
#     r = target_application("{ hello }")
#     breakpoint()
#     pass
