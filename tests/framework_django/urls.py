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

try:
    from django.conf.urls.defaults import url
except ImportError:
    try:
        from django.conf.urls import url
    except ImportError:
        from django.urls import re_path as url

import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^exception$', views.exception, name='exception'),
    url(r'^middleware_410$', views.middleware_410, name='middleware_410'),
    url(r'^permission_denied$', views.permission_denied,
            name='permission_denied'),
    url(r'^cbv$', views.MyView.as_view()),
    url(r'^deferred_cbv$', views.deferred_cbv),
    url(r'^html_insertion$', views.html_insertion, name='html_insertion'),
    url(r'^html_insertion_content_length$',
        views.html_insertion_content_length,
        name='html_insertion_content_length'),
    url(r'^html_insertion_manual$', views.html_insertion_manual,
        name='html_insertion_manual'),
    url(r'^html_insertion_unnamed_attachment_header$',
        views.html_insertion_unnamed_attachment_header,
        name='html_insertion_unnamed_attachment_header'),
    url(r'^html_insertion_named_attachment_header$',
        views.html_insertion_named_attachment_header,
        name='html_insertion_named_attachment_header'),
    url(r'^inclusion_tag$', views.inclusion_tag, name='inclusion_tag'),
    url(r'^template_tags$', views.template_tags, name='template_tags'),
    url(r'^render_exception_function', views.render_exception_function,
        name='render_exception_function'),
    url(r'^render_exception_class', views.RenderExceptionClass.as_view(),
        name='render_exception_class'),
    url(r'^gzip_html_insertion', views.gzip_html_insertion,
        name='gzip_html_insertion'),
]
