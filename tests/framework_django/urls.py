try:
    from django.conf.urls.defaults import url
except ImportError:
    from django.conf.urls import url

import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^exception$', views.exception, name='exception'),
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
]
