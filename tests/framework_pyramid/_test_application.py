import webtest

from pyramid.response import Response
from pyramid.view import view_config, view_defaults
from pyramid.config import Configurator
import pyramid.httpexceptions as exc

@view_config(route_name='home')
def home_view(request):
    return Response('<p>INDEX RESPONSE</p>')

@view_config(route_name='error')
def error(request):
    raise RuntimeError('error')

@view_config(route_name='not_found_exception_response')
def not_found_exception_response(request):
    raise exc.exception_response(404)

@view_config(route_name='raise_not_found')
def raise_not_found(request):
    raise exc.HTTPNotFound()

@view_config(route_name='return_not_found')
def return_not_found(request):
    return exc.HTTPNotFound()

@view_config(route_name='redirect')
def redirect(request):
    raise exc.HTTPFound(request.route_url('home'))

@view_defaults(route_name='rest')
class RestView:
    def __init__(self, request):
        self.request = request

    @view_config(request_method='GET')
    def get(self):
        return Response('Called GET')

    @view_config(request_method='POST')
    def post(self):
        return Response('Called POST')

config = Configurator()
config.add_route('home', '/')
config.add_route('error', '/error')
config.add_route('not_found_exception_response', '/nf1')
config.add_route('raise_not_found', '/nf2')
config.add_route('return_not_found', '/nf3')
config.add_route('redirect', '/redirect')
config.add_route('rest', '/rest')
config.scan()

application = config.make_wsgi_app()

_test_application = webtest.TestApp(application)
