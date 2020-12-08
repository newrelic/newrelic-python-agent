import webtest

from pyramid.response import Response
from pyramid.view import view_config
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


@view_config(route_name='html_insertion')
def html_insertion(request):
    return Response('<!DOCTYPE html><html><head>Some header</head>'
                    '<body><h1>My First Heading</h1><p>My first paragraph.</p>'
                    '</body></html>')


class RestView:
    def __init__(self, request):
        self.request = request

    @view_config(route_name='rest', request_method='GET')
    def get(self):
        return Response('Called GET')

    @view_config(route_name='rest', request_method='POST')
    def post(self):
        return Response('Called POST')


def simple_tween_factory(handler, registry):
    def simple_tween(request):
        return handler(request)

    return simple_tween


def target_application(with_tweens=False, tweens_explicit=False):
    settings = {}
    if with_tweens and tweens_explicit:
        settings['pyramid.tweens'] = [
            '_test_application:simple_tween_factory',
        ]

    config = Configurator(settings=settings)
    config.add_route('home', '/')
    config.add_route('html_insertion', '/html_insertion')
    config.add_route('error', '/error')
    config.add_route('not_found_exception_response', '/nf1')
    config.add_route('raise_not_found', '/nf2')
    config.add_route('return_not_found', '/nf3')
    config.add_route('redirect', '/redirect')
    config.add_route('rest', '/rest')
    if with_tweens:
        config.add_tween('_test_application:simple_tween_factory')
    config.scan()

    application = config.make_wsgi_app()

    _test_application = webtest.TestApp(application)

    return _test_application
