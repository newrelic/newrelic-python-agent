from django.core.wsgi import get_wsgi_application
from django.conf.urls import patterns, url
from piston.handler import BaseHandler
from piston.resource import Resource


class MyHandler(BaseHandler):
    methods_allowed = ('GET',)

    def read(self, request):
        return {"Hello": "World"}


urlpatterns = patterns('',
    url("^$", Resource(handler=MyHandler)),
)


def wsgi():
    return get_wsgi_application()
