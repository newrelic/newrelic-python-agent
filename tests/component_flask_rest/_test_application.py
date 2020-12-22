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
