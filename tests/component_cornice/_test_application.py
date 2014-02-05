import webtest

from pyramid.config import Configurator

import cornice
import cornice.resource

service = cornice.Service(name='service', path='/service',
        description="Service")

@service.get()
def cornice_service_get_info(request):
    return {'Hello': 'World'}

@cornice.resource.resource(collection_path='/resource', path='/resource/{id}')
class Resource(object):
    def __init__(self, request):
        self.request = request

    def collection_get(self):
        return { 'resource': ['1', '2'] }

    @cornice.resource.view(renderer='json')
    def get(self):
        return self.request.matchdict['id']

error = cornice.Service(name='error', path='/error', description="Error")

@error.get()
def cornice_error_get_info(request):
    raise RuntimeError('error')

config = Configurator()
config.include("cornice")
config.scan()

application = config.make_wsgi_app()

_test_application = webtest.TestApp(application)
