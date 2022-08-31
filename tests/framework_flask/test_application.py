# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest

from testing_support.fixtures import (
    override_application_settings,
    validate_tt_parenting)
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_transaction_errors import validate_transaction_errors

from newrelic.packages import six

from conftest import async_handler_support, skip_if_not_async_handler_support

try:
    # The __version__ attribute was only added in 0.7.0.
    # Flask team does not use semantic versioning during development.
    from flask import __version__ as flask_version
    flask_version = tuple([int(v) for v in flask_version.split('.')])
    is_gt_flask060 = True
    is_dev_version = False
except ValueError:
    is_gt_flask060 = True
    is_dev_version = True
except ImportError:
    is_gt_flask060 = False
    is_dev_version = False

requires_endpoint_decorator = pytest.mark.skipif(not is_gt_flask060,
        reason="The endpoint decorator is not supported.")


def target_application():
    # We need to delay Flask application creation because of ordering
    # issues whereby the agent needs to be initialised before Flask is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as we will then get view handler
    # functions are different between Python 2 and 3, with the latter
    # showing <local> scope in path.

    if not async_handler_support:
        from _test_application import _test_application
    else:
        from _test_application_async import _test_application
    return _test_application


_test_application_index_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:index_page', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

_test_application_index_tt_parenting = (
    'TransactionNode', [
        ('FunctionNode', [
            ('FunctionNode', [
                ('FunctionNode', []),
                ('FunctionNode', []),
                ('FunctionNode', []),
                # some flask versions have more FunctionNodes here, as appended
                # below
            ]),
        ]),
        ('FunctionNode', []),
        ('FunctionNode', [
            ('FunctionNode', []),
        ]),
    ]
)

if is_dev_version or (is_gt_flask060 and flask_version >= (0, 7)):
    _test_application_index_tt_parenting[1][0][1][0][1].append(
        ('FunctionNode', []),
    )
if is_dev_version or (is_gt_flask060 and flask_version >= (0, 9)):
    _test_application_index_tt_parenting[1][0][1][0][1].append(
        ('FunctionNode', []),
    )

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:index_page',
        scoped_metrics=_test_application_index_scoped_metrics)
@validate_tt_parenting(_test_application_index_tt_parenting)
@validate_code_level_metrics("_test_application", "index_page")
def test_application_index():
    application = target_application()
    response = application.get('/index')
    response.mustcontain('INDEX RESPONSE')

_test_application_async_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application_async:async_page', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]

@skip_if_not_async_handler_support
@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application_async:async_page',
        scoped_metrics=_test_application_async_scoped_metrics)
@validate_tt_parenting(_test_application_index_tt_parenting)
@validate_code_level_metrics("_test_application_async", "async_page")
def test_application_async():
    application = target_application()
    response = application.get('/async')
    response.mustcontain('ASYNC RESPONSE')

_test_application_endpoint_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:endpoint_page', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:endpoint_page',
        scoped_metrics=_test_application_endpoint_scoped_metrics)
@validate_code_level_metrics("_test_application", "endpoint_page")
def test_application_endpoint():
    application = target_application()
    response = application.get('/endpoint')
    response.mustcontain('ENDPOINT RESPONSE')


_test_application_error_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:error_page', 1),
        ('Function/flask.app:Flask.handle_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Function/flask.app:Flask.handle_user_exception', 1),
        ('Function/flask.app:Flask.handle_user_exception', 1)]


if six.PY3:
    _test_application_error_errors = ['builtins:RuntimeError']
else:
    _test_application_error_errors = ['exceptions:RuntimeError']


@validate_transaction_errors(errors=_test_application_error_errors)
@validate_transaction_metrics('_test_application:error_page',
        scoped_metrics=_test_application_error_scoped_metrics)
@validate_code_level_metrics("_test_application", "error_page")
def test_application_error():
    application = target_application()
    application.get('/error', status=500, expect_errors=True)


_test_application_abort_404_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:abort_404_page', 1),
        ('Function/flask.app:Flask.handle_http_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Function/flask.app:Flask.handle_user_exception', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:abort_404_page',
        scoped_metrics=_test_application_abort_404_scoped_metrics)
@validate_code_level_metrics("_test_application", "abort_404_page")
def test_application_abort_404():
    application = target_application()
    application.get('/abort_404', status=404)


_test_application_exception_404_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:exception_404_page', 1),
        ('Function/flask.app:Flask.handle_http_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Function/flask.app:Flask.handle_user_exception', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:exception_404_page',
        scoped_metrics=_test_application_exception_404_scoped_metrics)
@validate_code_level_metrics("_test_application", "exception_404_page")
def test_application_exception_404():
    application = target_application()
    application.get('/exception_404', status=404)


_test_application_not_found_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/flask.app:Flask.handle_http_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Function/flask.app:Flask.handle_user_exception', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('flask.app:Flask.handle_http_exception',
        scoped_metrics=_test_application_not_found_scoped_metrics)
def test_application_not_found():
    application = target_application()
    application.get('/missing', status=404)


_test_application_render_template_string_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:template_string', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Template/Compile/<template>', 1),
        ('Template/Render/<template>', 1)]


@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_application:template_string',
        scoped_metrics=_test_application_render_template_string_scoped_metrics)
@validate_code_level_metrics("_test_application", "template_string")
def test_application_render_template_string():
    application = target_application()
    application.get('/template_string')


_test_application_render_template_not_found_scoped_metrics = [
        ('Function/flask.app:Flask.wsgi_app', 1),
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/_test_application:template_not_found', 1),
        ('Function/flask.app:Flask.handle_exception', 1),
        ('Function/werkzeug.wsgi:ClosingIterator.close', 1),
        ('Function/flask.app:Flask.handle_user_exception', 1)]


@validate_transaction_errors(errors=['jinja2.exceptions:TemplateNotFound'])
@validate_transaction_metrics('_test_application:template_not_found',
    scoped_metrics=_test_application_render_template_not_found_scoped_metrics)
def test_application_render_template_not_found():
    application = target_application()
    application.get('/template_not_found', status=500, expect_errors=True)


_test_html_insertion_settings = {
    'browser_monitoring.enabled': True,
    'browser_monitoring.auto_instrument': True,
    'js_agent_loader': u'<!-- NREUM HEADER -->',
}


@override_application_settings(_test_html_insertion_settings)
def test_html_insertion():
    application = target_application()
    response = application.get('/html_insertion', status=200)

    # The 'NREUM HEADER' value comes from our override for the header.
    # The 'NREUM.info' value comes from the programmatically generated
    # footer added by the agent.

    response.mustcontain('NREUM HEADER', 'NREUM.info')
