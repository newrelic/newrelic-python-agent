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
from flask import Blueprint
from werkzeug.routing import Rule

from conftest import is_flask_v2 as nested_blueprint_support

# Blueprints are only available in 0.7.0 onwards.

blueprint = Blueprint('blueprint', __name__)

application = Flask(__name__)

@blueprint.route('/index')
def index_page():
    return 'BLUEPRINT INDEX RESPONSE'

@blueprint.endpoint('endpoint')
def endpoint_page():
    return 'BLUEPRINT ENDPOINT RESPONSE'

@blueprint.before_app_first_request
def before_app_first_request():
    pass

@blueprint.before_request
def before_request():
    pass

@blueprint.before_app_request
def before_app_request():
    pass

@blueprint.after_request
def after_request(response):
    return response

@blueprint.after_app_request
def after_app_request(response):
    return response

@blueprint.teardown_request
def teardown_request(exc):
    pass

@blueprint.teardown_app_request
def teardown_app_request(exc):
    pass

# Support for nested blueprints was added in Flask 2.0
if nested_blueprint_support:
    parent = Blueprint('parent', __name__, url_prefix='/parent')
    child = Blueprint('child', __name__, url_prefix='/child')

    parent.register_blueprint(child)

    @child.route('/nested')
    def nested_page():
        return 'PARENT NESTED RESPONSE'
    application.register_blueprint(parent)

application.register_blueprint(blueprint)


application.url_map.add(Rule('/endpoint', endpoint='endpoint'))

_test_application = webtest.TestApp(application)
