import webtest

from flask import Flask
from werkzeug.exceptions import HTTPException


class CustomException(Exception):
    pass


def create_app(module):
    app = Flask(__name__)
    api = module.Api(app)


    class IndexResource(module.Resource):
        def get(self):
            return {'hello': 'world'}


    class ExceptionResource(module.Resource):
        def get(self, exception, code):
            if 'HTTPException' in exception:
                e = HTTPException()
            elif 'CustomException' in exception:
                e = CustomException()
            else:
                raise AssertionError('Unexpected exception received: %s' %
                        exception)
            e.code = code
            raise e


    api.add_resource(IndexResource, '/index', endpoint="index")
    api.add_resource(ExceptionResource, '/exception/<string:exception>/<int:code>', endpoint="exception")

    return app


def get_test_application(module, propagate_exceptions=False):
    app = create_app(module)
    app.config['PROPAGATE_EXCEPTIONS'] = propagate_exceptions
    test_application = webtest.TestApp(app)
    return test_application
