try:
    from django.conf.urls.defaults import patterns, url
except ImportError:    
    from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'views.index', name='index'),
)
