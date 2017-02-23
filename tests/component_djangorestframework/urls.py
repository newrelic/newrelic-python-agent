try:
    from django.conf.urls.defaults import patterns, url
except ImportError:
    from django.conf.urls import patterns, url

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

class View(APIView):
    def get(self, request, format=None):
        return Response([{"a":"b"}])

class Error(Exception): pass

class ViewError(APIView):
    def get(self, request, format=None):
        raise Error('xxx')

@api_view(http_method_names=['GET'])
def wrapped_view(request):
    return Response({'message': 'wrapped_view response'})

urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
    url(r'^view/$', View.as_view()),
    url(r'^view_error/$', ViewError.as_view()),
    url(r'^api_view/$', wrapped_view),
)
