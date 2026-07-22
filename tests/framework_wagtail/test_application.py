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
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics

def target_application():
    from _target_application import _target_application

    return _target_application


@validate_transaction_metrics(
    "dummy_app.models:HomePage.route",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/wagtail.views:serve", 1),
    ],
)
def test_home():
    test_application = target_application()
    response = test_application.get("/")


@validate_transaction_metrics(
    "dummy_app.models:RoutablePage.index_route",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/wagtail.views:serve", 1),
    ],
)
def test_routable():
    test_application = target_application()
    response = test_application.get("/routable/")


@validate_transaction_metrics(
    "dummy_app.models:RoutablePage.index",
    scoped_metrics=[
        ("Function/django.core.handlers.wsgi:WSGIHandler.__call__", 1),
        ("Python/WSGI/Application", 1),
        ("Python/WSGI/Response", 1),
        ("Python/WSGI/Finalize", 1),
        ("Function/wagtail.views:serve", 1),
    ],
)
def test_routable_routable():
    test_application = target_application()
    response = test_application.get("/routable/routable/")
