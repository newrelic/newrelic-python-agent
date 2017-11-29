try:
    from django.conf.urls.defaults import patterns, url
except ImportError:
    from django.conf.urls import patterns, url

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView


class View(APIView):
    def get(self, request, format=None):
        return Response([{'message': 'restframework view response'}])


class Error(Exception):
    pass


class ViewError(APIView):
    def get(self, request, format=None):
        raise Error('xxx')


class ViewHandleError(APIView):
    def get(self, request, status, global_exc):
        self.status = int(status)
        self.global_exc = global_exc == 'True'
        raise Error('omg cats')

    def get_exception_handler(self):
        return self._exception_handler

    def _exception_handler(self, exc, context):
        return Response([{'response': 'exception was handled global'}],
                status=self.status)

    def handle_exception(self, exc):
        if self.global_exc:
            return super(ViewHandleError, self).handle_exception(exc)
        else:
            return Response([{'response': 'exception was handled not global'}],
                    status=self.status)


@api_view(http_method_names=['GET'])
def wrapped_view(request):
    return Response({'message': 'wrapped_view response'})


urlpatterns = patterns('',
    url(r'^$', 'views.index', name='index'),
    url(r'^view/$', View.as_view()),
    url(r'^view_error/$', ViewError.as_view()),
    url(r'^view_handle_error/(?P<status>\w+)/(?P<global_exc>\w+)/$',
        ViewHandleError.as_view()),
    url(r'^api_view/$', wrapped_view),
)
