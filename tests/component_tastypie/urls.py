try:
    from django.conf.urls import url, include
except ImportError:
    from django.conf.urls.defaults import url, include

from tastypie.api import Api

import views

from api import SimpleResource

simple_resource = SimpleResource()

urlpatterns = [
    url(r'^index/$', views.index, name='index'),
    url(r'^api/v1/', include(simple_resource.urls)),
]

v2_api = Api(api_name='v2')
v2_api.register(SimpleResource())

urlpatterns += [
    url(r'^api/', include(v2_api.urls)),
]
