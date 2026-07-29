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
import os

import pytest
from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,  # autouse fixture, must be importable in this module
)

_default_settings = {
    "package_reporting.enabled": False,  # Turn off package reporting for testing as it causes slow downs.
    "transaction_tracer.explain_threshold": 0.0,
    "transaction_tracer.transaction_threshold": 0.0,
    "transaction_tracer.stack_trace_threshold": 0.0,
    "debug.log_data_collector_payloads": True,
    "debug.record_transaction_failure": True,
    "debug.log_autorum_middleware": True,
}

collector_agent_registration = collector_agent_registration_fixture(
    app_name="Python Agent Test (framework_wagtail)", default_settings=_default_settings, scope="module"
)


@pytest.fixture(autouse=True)
def database():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    import django

    django.setup()
    from django.core.management import call_command

    call_command("migrate", verbosity=0, interactive=False, run_syncdb=True)

    # Wagtail's own migrations seed a default "Welcome" home page (a plain
    # ``Page``) and a default ``Site``. Replace that root with a ``HomePage``
    # and hang a ``RoutablePage`` beneath it so that "/" and "/routable/"
    # resolve to real, renderable pages served by the dummy_app page types.
    from dummy_app.models import HomePage, RoutablePage
    from wagtail.models import Page, Site

    if not HomePage.objects.exists():
        site = Site.objects.get(is_default_site=True)
        default_home = site.root_page
        home = Page.objects.get(depth=1).add_child(instance=HomePage(title="Home", slug="home-page"))
        site.root_page = home
        site.save()
        default_home.delete()
        home.add_child(instance=RoutablePage(title="Routable", slug="routable"))
