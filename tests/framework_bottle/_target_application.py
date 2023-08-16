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

import webtest
from bottle import HTTPError, default_app, error, route

from newrelic.common.package_version_utils import get_package_version_tuple

version = get_package_version_tuple("bottle")


@route("/index")
def index_page():
    return "INDEX RESPONSE"


@route("/error")
def error_page():
    raise RuntimeError("RUNTIME ERROR")


@error(404)
def error404_page(error):
    return "NOT FOUND"


@route("/html_insertion")
def html_insertion_page():
    return (
        "<!DOCTYPE html><html><head>Some header</head>"
        "<body><h1>My First Heading</h1><p>My first paragraph.</p>"
        "</body></html>"
    )


if version >= (0, 9, 0):
    from bottle import auth_basic  # pylint: disable=ungrouped-imports

    def auth_check(username, password):
        return username == "user" and password == "password"  # nosec

    @route("/auth")
    @auth_basic(auth_check)
    def auth_basic_page():
        return "AUTH OKAY"

    def plugin_error(callback):
        def wrapper(*args, **kwargs):
            raise HTTPError(403, "Forbidden")

        return wrapper

    @route("/plugin_error", apply=[plugin_error], skip=["json"])
    def plugin_error_page():
        return "PLUGIN RESPONSE"


application = default_app()
target_application = webtest.TestApp(application)
