import webtest
import pytest

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_application_settings)

@pytest.fixture()
def target_application(request):
    import gluon.main
    return webtest.TestApp(gluon.main.wsgibase)

_test_application_index_scoped_metrics = [
        ('Function/gluon.main:wsgibase', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Python/Web2Py/Models/default/index', 1),
        ('Script/Execute/models/db.py', 1),
        ('Script/Execute/models/menu.py', 1),
        ('Python/Web2Py/Controller/default/index', 1),
        ('Script/Execute/controllers/default.py', 1),
        ('Python/Web2Py/View/default/index', 1),
        ('Template/Compile/views/default/index.html', 1),
        ('Template/Render/views/default/index.html', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('welcome::default/index.html', group='Web2Py',
        scoped_metrics=_test_application_index_scoped_metrics)
def test_application_index(target_application):
    response = target_application.get('/welcome/default/index')
    #response.mustcontain('INDEX RESPONSE')

_test_application_index_scoped_metrics = [
        ('Function/gluon.main:wsgibase', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Python/Web2Py/Models/simple_examples/hello1', 1),
        ('Script/Execute/models/db.py', 1),
        ('Script/Execute/models/feeds_reader.py', 1),
        ('Script/Execute/models/markmin.py', 1),
        ('Script/Execute/models/menu.py', 1),
        ('Python/Web2Py/Controller/simple_examples/hello1', 1),
        ('Script/Execute/controllers/simple_examples.py', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('examples::simple_examples/hello1.html',
        group='Web2Py', scoped_metrics=_test_application_index_scoped_metrics)
def test_application_controller(target_application):
    response = target_application.get('/examples/simple_examples/hello1')
    #response.mustcontain('INDEX RESPONSE')

_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}

@override_application_settings(_test_html_insertion_settings)
def test_html_insertion(target_application):
    response = target_application.get('/welcome/default/index')

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')
