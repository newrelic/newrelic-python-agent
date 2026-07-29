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

import django.db.models.deletion
import wagtail.contrib.routable_page.models
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wagtailcore", "0070_rename_pagerevision_revision")]

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
                )
            ],
            options={"abstract": False},
            bases=("wagtailcore.page",),
        ),
        migrations.AddField(model_name="homepage", name="body", field=wagtail.fields.RichTextField(blank=True)),
        migrations.CreateModel(
            name="RoutablePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                )
            ],
            options={"verbose_name": "Routable page"},
            bases=(wagtail.contrib.routable_page.models.RoutablePage,),
        ),
        migrations.AddField(model_name="routablepage", name="body", field=wagtail.fields.RichTextField(blank=True)),
    ]
