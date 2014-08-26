try:
    from django.conf.urls.defaults import patterns, url, include
except ImportError:
    from django.conf.urls import patterns, url, include

from rest_framework.views import APIView
from rest_framework.response import Response

class View(APIView):
    def get(self, request, format=None):
        return Response([{"a":"b"}])

class Error(Exception): pass

class ViewError(APIView):
    def get(self, request, format=None):
        raise Error('xxx')

urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
    url(r'^view/$', View.as_view()),
    url(r'^view_error/$', ViewError.as_view()),
)
