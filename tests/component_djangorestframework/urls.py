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

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.settings import APISettings, api_settings
from views import index


class View(APIView):
    def get(self, request, format=None):
        return Response([{'message': 'restframework view response'}])


class Error(Exception):
    pass


class ViewError(APIView):
    def get(self, request, format=None):
        raise Error('xxx')


class ViewHandleError(APIView):
    settings = APISettings(api_settings.user_settings,
            api_settings.defaults, api_settings.import_strings)

    def get(self, request, status, global_exc):
        self.status = int(status)
        self.global_exc = global_exc == 'True'
        raise Error('omg cats')

    def _exception_handler(self, exc, context=None):
        if context:
            status = int(context['kwargs']['status'])
        else:
            status = self.status
        return Response([{'response': 'exception was handled global'}],
                status=status)

    def get_exception_handler(self):
        return self.settings.EXCEPTION_HANDLER

    def handle_exception(self, exc):
        self.settings.EXCEPTION_HANDLER = self._exception_handler
        if self.global_exc:
            return super(ViewHandleError, self).handle_exception(exc)
        else:
            return Response([{'response': 'exception was handled not global'}],
                    status=self.status)


@api_view(http_method_names=['GET'])
def wrapped_view(request):
    return Response({'message': 'wrapped_view response'})


urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^view/$', View.as_view()),
    url(r'^view_error/$', ViewError.as_view()),
    url(r'^view_handle_error/(?P<status>\d+)/(?P<global_exc>\w+)/$',
        ViewHandleError.as_view()),
    url(r'^api_view/$', wrapped_view),
]
