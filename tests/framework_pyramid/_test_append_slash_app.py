import webtest

from pyramid.response import Response
from pyramid.view import view_config, notfound_view_config
from pyramid.config import Configurator
import pyramid.httpexceptions as exc


@view_config(route_name='home')
def home_view(request):
    return Response('<p>INDEX RESPONSE</p>')

@notfound_view_config(append_slash=True)
def not_found(request):
    return Response('<p>NOT FOUND</p>', status='404 Not Found')

config = Configurator()
config.add_route('home', '/')
config.scan()

application = config.make_wsgi_app()

_test_application = webtest.TestApp(application)
