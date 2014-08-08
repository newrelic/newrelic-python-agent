try:
    from django.conf.urls.defaults import patterns, url
except ImportError:
    from django.conf.urls import patterns, url

from views import MyView

urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
    url(r'^cbv$', MyView.as_view()),
    url(r'^deferred_cbv$', 'views.deferred_cbv'),
    url(r'^html_insertion$', 'views.html_insertion', name='html_insertion'),
    url(r'^html_insertion_unnamed_attachment_header$',
        'views.html_insertion_unnamed_attachment_header',
        name='html_insertion_unnamed_attachment_header'),
    url(r'^html_insertion_named_attachment_header$',
        'views.html_insertion_named_attachment_header',
        name='html_insertion_named_attachment_header'),
)
