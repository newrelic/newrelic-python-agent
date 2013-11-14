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

if is_gt_flask060:
    @application.errorhandler(404)
    def page_not_found(error):
        return 'This page does not exist', 404

requires_error_handler = pytest.mark.skipif(is_gt_flask060,
        reason="The error handler decorator is not supported.")

test_application = webtest.TestApp(application)

@requires_error_handler
def test_error_handler_not_found():
    response = test_application.get('/missing', status=404)
