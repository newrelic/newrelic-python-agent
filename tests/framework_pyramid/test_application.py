import pytest

def test_application():
    # We need to delay Pyramid application creation because of ordering
    # issues whereby the agent needs to be initialised before Pyramid is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as Pyramid relies on view handlers being
    # at global scope, so import it from a separate module.

    from _test_application import _test_application
    return _test_application

def test_application_index():
    application = test_application()
    response = application.get('')
    response.mustcontain('INDEX RESPONSE')

def test_application_index_agent_disabled():
    environ = { 'newrelic.enabled': False }
    application = test_application()
    response = application.get('', extra_environ=environ)
    response.mustcontain('INDEX RESPONSE')

def test_application_not_found_as_exception_response():
    application = test_application()
    application.get('/nf1', status=404)

def test_application_not_found_raises_NotFound():
    application = test_application()
    application.get('/nf2', status=404)

def test_application_not_found_returns_NotFound():
    application = test_application()
    application.get('/nf3', status=404)

def test_application_unexpected_exception():
    application = test_application()
    with pytest.raises(RuntimeError):
        application.get('/error', status=500)

def test_application_redirect():
    application = test_application()
    application.get('/redirect', status=302)

def test_application_rest_calls():
    application = test_application()
    response = application.get('/rest')
    response.mustcontain('Called GET')
    response = application.post('/rest') # Raises PredicateMismatch
    response.mustcontain('Called POST')
