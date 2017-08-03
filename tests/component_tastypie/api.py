from tastypie.resources import Resource
from tastypie.exceptions import NotFound


class SimpleResource(Resource):
    class Meta:
        resource_name = 'simple'

    def obj_get(self, *args, **kwargs):
        raise NotFound('Whatever it was you were looking for, it isn\'t here')
