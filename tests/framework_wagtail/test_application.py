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

from testing_support.fixtures import (
    collector_agent_registration_fixture,
    collector_available_fixture,
    override_application_settings,
    override_generic_settings,
    override_ignore_status_codes,
)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics


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
    app_name="Python Agent Test (framework_django)", default_settings=_default_settings, scope="module"
)

@pytest.fixture
def database():

def create_homepage(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    Page = apps.get_model("wagtailcore.Page")
    Site = apps.get_model("wagtailcore.Site")
    HomePage = apps.get_model("home.HomePage")

    # Delete the default homepage
    # If migration is run multiple times, it may have already been deleted
    Page.objects.filter(id=2).delete()

    # Create content type for homepage model
    homepage_content_type, __ = ContentType.objects.get_or_create(
        model="homepage", app_label="home"
    )

    # Create a new homepage
    homepage = HomePage.objects.create(
        title="Home",
        draft_title="Home",
        slug="home",
        content_type=homepage_content_type,
        path="00010001",
        depth=2,
        numchild=0,
        url_path="/home/",
    )

    # Create a site with the new homepage set as the root
    Site.objects.create(hostname="localhost", root_page=homepage, is_default_site=True)

def remove_homepage(apps, schema_editor):
    # Get models
    ContentType = apps.get_model("contenttypes.ContentType")
    HomePage = apps.get_model("home.HomePage")

    # Delete the default homepage
    # Page and Site objects CASCADE
    HomePage.objects.filter(slug="home", depth=2).delete()

    # Delete content type for homepage model
    ContentType.objects.filter(model="homepage", app_label="home").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0040_page_draft_title"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        parent_link=True,
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.Page",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.RunPython(create_homepage, remove_homepage),
        migrations.AddField(
            model_name='homepage',
            name='body',
            field=wagtail.fields.RichTextField(blank=True),
        ),
        migrations.CreateModel(
            name='RoutablePage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
            ],
            options={
                'verbose_name': 'Routable page',
            },
            bases=(wagtail.contrib.routable_page.models.RoutablePage,),
        ),
        migrations.AddField(
            model_name='routablepage',
            name='body',
            field=wagtail.fields.RichTextField(blank=True),
        ),
    ]


def target_application():
    from _target_application import _target_application

    return _target_application


@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/views:index", 1),
    ]
)
def test_home():
    test_application = target_application()
    response = test_application.get("")


@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/views:index", 1),
    ]
)
def test_routable():
    test_application = target_application()
    response = test_application.get("/routable")


@validate_transaction_metrics(
    "views:index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/views:index", 1),
    ]
)
def test_routable_routable():
    test_application = target_application()
    response = test_application.get("/routable/routable")
