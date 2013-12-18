import pytest

try:
    # The __version__ attribute was only added in 0.7.0.
    from flask import __version__ as flask_version
    is_gt_flask060 = True
except ImportError:
    is_gt_flask060 = False

requires_error_handler = pytest.mark.skipif(not is_gt_flask060,
        reason="The error handler decorator is not supported.")

def test_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_not_found import _test_application
    return _test_application

@requires_error_handler
def test_error_handler_not_found():
    application = test_application()
    response = application.get('/missing', status=404)
