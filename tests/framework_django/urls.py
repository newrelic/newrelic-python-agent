try:
    from django.conf.urls.defaults import patterns, url
except ImportError:    
    from django.conf.urls import patterns, url

from views import MyView

urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
    url(r'^cbv$', MyView.as_view()),
    url(r'^deferred_cbv$', 'views.deferred_cbv')
)
