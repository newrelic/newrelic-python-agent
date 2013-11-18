import pytest
import webtest

from flask import Flask, redirect

application = Flask(__name__)

try:
    # The __version__ attribute was only added in 0.7.0.
    from flask import __version__ as flask_version
    is_gt_flask060 = True
except ImportError:
    is_gt_flask060 = False

class UserException(Exception):
    pass

if is_gt_flask060:
    @application.errorhandler(UserException)
    def page_not_found(error):
        return 'USER EXCEPTION', 500

@application.route('/user_exception')
def error_page():
    raise UserException('User exception.')

requires_error_handler = pytest.mark.skipif(not is_gt_flask060,
        reason="The error handler decorator is not supported.")

test_application = webtest.TestApp(application)

@requires_error_handler
def test_user_exception_handler():
    response = test_application.get('/user_exception', status=500)
    response.mustcontain('USER EXCEPTION')
