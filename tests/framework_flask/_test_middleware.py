import webtest

from flask import Flask

application = Flask(__name__)

@application.before_first_request
def before_first_request():
    pass

@application.before_request
def before_request():
    pass

@application.after_request
def after_request(response):
    return response

@application.teardown_request
def teardown_request(exc):
    pass

@application.teardown_appcontext
def teardown_appcontext(exc):
    pass

@application.route('/middleware')
def index_page():
    return 'INDEX RESPONSE'

_test_application = webtest.TestApp(application)
