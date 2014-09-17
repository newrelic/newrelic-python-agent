import webtest

from flask import Flask
from flask import Blueprint
from werkzeug.routing import Rule

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

application.register_blueprint(blueprint)

application.url_map.add(Rule('/endpoint', endpoint='endpoint'))

_test_application = webtest.TestApp(application)
