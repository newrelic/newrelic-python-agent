try:
    from django.conf.urls import url, include
except ImportError:
    from django.conf.urls.defaults import url, include

import views

from api import SimpleResource

simple_resource = SimpleResource()

urlpatterns = [
    url(r'^index/$', views.index, name='index'),
    url(r'^api/', include(simple_resource.urls)),
]
