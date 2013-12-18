def test_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    from _test_application import _test_application
    return _test_application

def test_application_index():
    application = test_application()
    response = application.get('/index')
    response.mustcontain('INDEX RESPONSE')

def test_application_error():
    application = test_application()
    response = application.get('/error', status=500, expect_errors=True)

def test_application_abort_404():
    application = test_application()
    response = application.get('/abort_404', status=404)

def test_application_not_found():
    application = test_application()
    response = application.get('/missing', status=404)

def test_application_render_template_string():
    application = test_application()
    response = application.get('/template_string')

def test_application_render_template_not_found():
    application = test_application()
    response = application.get('/template_not_found', status=500)
