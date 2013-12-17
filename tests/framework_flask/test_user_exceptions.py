import pytest
import webtest

from flask import Flask, redirect

try:
    # The __version__ attribute was only added in 0.7.0.
    from flask import __version__ as flask_version
    is_gt_flask060 = True
except ImportError:
    is_gt_flask060 = False

requires_error_handler = pytest.mark.skipif(not is_gt_flask060,
        reason="The error handler decorator is not supported.")

class UserException(Exception):
    pass

_test_application = None

def test_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late.

    global _test_application

    if _test_application:
        return _test_application

    application = Flask(__name__)

    application = Flask(__name__)

    @application.errorhandler(UserException)
    def page_not_found(error):
        return 'USER EXCEPTION', 500

    @application.route('/user_exception')
    def error_page():
        raise UserException('User exception.')

    _test_application = webtest.TestApp(application)

    return _test_application

@requires_error_handler
def test_user_exception_handler():
    application = test_application()
    response = application.get('/user_exception', status=500)
    response.mustcontain('USER EXCEPTION')
