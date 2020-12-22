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

import webtest

from pyramid.response import Response
from pyramid.view import view_config
from pyramid.config import Configurator
import pyramid.httpexceptions as exc


@view_config(route_name="home")
def home_view(request):
    return Response("<p>INDEX RESPONSE</p>")


@view_config(route_name="error")
def error(request):
    raise RuntimeError("error")


@view_config(route_name="not_found_exception_response")
def not_found_exception_response(request):
    raise exc.exception_response(404)


@view_config(route_name="raise_not_found")
def raise_not_found(request):
    raise exc.HTTPNotFound()


@view_config(route_name="return_not_found")
def return_not_found(request):
    return exc.HTTPNotFound()


@view_config(route_name="redirect")
def redirect(request):
    raise exc.HTTPFound(request.route_url("home"))


@view_config(route_name="html_insertion")
def html_insertion(request):
    return Response(
        "<!DOCTYPE html><html><head>Some header</head>"
        "<body><h1>My First Heading</h1><p>My first paragraph.</p>"
        "</body></html>"
    )


class RestView:
    def __init__(self, request):
        self.request = request

    @view_config(route_name="rest", request_method="GET")
    def get(self):
        return Response("Called GET")

    @view_config(route_name="rest", request_method="POST")
    def post(self):
        return Response("Called POST")


def simple_tween_factory(handler, registry):
    def simple_tween(request):
        return handler(request)

    return simple_tween


# CORNICE SECTION
try:
    import cornice
    import cornice.resource
except ImportError:
    cornice = None
else:
    service = cornice.Service(name="service", path="/service", description="Service")


    @service.get()
    def cornice_service_get_info(request):
        return {"Hello": "World"}


    @cornice.resource.resource(collection_path="/resource", path="/resource/{id}")
    class Resource(object):
        def __init__(self, request, context=None):
            self.request = request

        def collection_get(self):
            return {"resource": ["1", "2"]}

        @cornice.resource.view(renderer="json")
        def get(self):
            return self.request.matchdict["id"]


    cornice_error = cornice.Service(
        name="cornice_error", path="/cornice_error", description="Error"
    )


    @cornice_error.get()
    def cornice_error_get_info(request):
        raise RuntimeError("error")


# END CORNICE SECTION


def target_application(with_tweens=False, tweens_explicit=False, handle_exceptions=False):
    settings = {}
    if with_tweens and tweens_explicit:
        settings["pyramid.tweens"] = [
            "_test_application:simple_tween_factory",
        ]

    config = Configurator(settings=settings)
    if cornice:

        # Use an execution policy which doesn't re-trigger the error handler
        def execution_policy(environ, router):
            with router.request_context(environ) as request:
                return router.invoke_request(request)

        config.set_execution_policy(execution_policy)
        config.add_settings(handle_exceptions=handle_exceptions)
        config.include("cornice")

    config.add_route("home", "/")
    config.add_route("html_insertion", "/html_insertion")
    config.add_route("error", "/error")
    config.add_route("not_found_exception_response", "/nf1")
    config.add_route("raise_not_found", "/nf2")
    config.add_route("return_not_found", "/nf3")
    config.add_route("redirect", "/redirect")
    config.add_route("rest", "/rest")
    if with_tweens:
        config.add_tween("_test_application:simple_tween_factory")
    config.scan()

    application = config.make_wsgi_app()

    _test_application = webtest.TestApp(application)

    return _test_application
