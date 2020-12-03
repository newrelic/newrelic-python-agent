import webtest

from flask import Flask

class UserException(Exception):
    pass

application = Flask(__name__)

@application.errorhandler(UserException)
def page_not_found(error):
    return 'USER EXCEPTION', 500

@application.route('/user_exception')
def error_page():
    raise UserException('User exception.')

_test_application = webtest.TestApp(application)
