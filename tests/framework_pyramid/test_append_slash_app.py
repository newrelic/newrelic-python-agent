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

"""These tests check two things:

    1. Using a notfound_view will name the transaction after the not_found
       view, not the default_exceptionresponse_view. There can only be one
       notfound_view per Pyramid application, so to test both cases (default
       and user-defined notfound_view), we use 2 separate apps.

    2. Verifying that we don't double wrap the notfound_view. Because
       we instrument Configurator._derive_view(), and because
       Configurator._derive_view() is called twice when adding a
       notfound_view (once in add_notfound_view(), and again in add_view()),
       our instrumentation checks to see if a view has already been
       wrapped before wrapping.

       If our check fails, then the metric '_test_append_slash_app:not_found'
       will have a count of 2.
"""

import pkg_resources
import pytest
import re

from testing_support.fixtures import (validate_transaction_metrics,
    validate_transaction_errors, override_application_settings)


def _to_int(version_str):
    m = re.match(r'\d+', version_str)
    return int(m.group(0)) if m else 0

def pyramid_version():
    s = pkg_resources.get_distribution('pyramid').version
    return tuple([_to_int(c) for c in s.split('.')[:2]])

# Defining a `pytestmark` at the module level means py.test will apply
# this `skipif` conditional to all tests in the module.

pytestmark = pytest.mark.skipif(pyramid_version() < (1, 3),
        reason='requires pyramid >= (1, 3)')

def target_application():
    # We need to delay Pyramid application creation because of ordering
    # issues whereby the agent needs to be initialised before Pyramid is
    # imported and the routes configured. Normally pytest only runs the
    # global fixture which will initialise the agent after each test
    # file is imported, which is too late. We also can't do application
    # creation within a function as Pyramid relies on view handlers being
    # at global scope, so import it from a separate module.

    from _test_append_slash_app import _test_application
    return _test_application

_test_append_slash_app_index_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/_test_append_slash_app:home_view', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_append_slash_app:home_view',
        scoped_metrics=_test_append_slash_app_index_scoped_metrics)
def test_index():
    application = target_application()
    response = application.get('/')
    response.mustcontain('INDEX RESPONSE')

_test_not_found_append_slash_scoped_metrics = [
        ('Python/WSGI/Application', 1),
        ('Python/WSGI/Response', 1),
        ('Python/WSGI/Finalize', 1),
        ('Function/pyramid.router:Router.__call__', 1),
        ('Function/pyramid.view:AppendSlashNotFoundViewFactory', 1),
        ('Function/_test_append_slash_app:not_found', 1)]

@validate_transaction_errors(errors=[])
@validate_transaction_metrics('_test_append_slash_app:not_found',
        scoped_metrics=_test_not_found_append_slash_scoped_metrics)
def test_not_found_append_slash():
    application = target_application()
    response = application.get('/foo', status=404)
    response.mustcontain('NOT FOUND')
