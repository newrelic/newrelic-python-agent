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

from django.db import models
from wagtail.contrib.routable_page.models import RoutablePage, re_path
from wagtail.fields import RichTextField
from wagtail.models import Page


class HomePage(Page):
    body = RichTextField(blank=True)

    content_panels = [*Page.content_panels, "body"]


class RoutablePage(RoutablePage):
    body = RichTextField(blank=True)

    content_panels = [*Page.content_panels, "body"]

    @re_path(r"^routable")
    def index(self, request):
        # Handle URLs of the form /<id>
        return super().serve(request)

    class Meta:
        verbose_name = "Routable page"

    def __str__(self):
        return "Page from routable"
