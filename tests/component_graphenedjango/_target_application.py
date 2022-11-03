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


import json

import pytest
import webtest

from .wsgi import application


def check_response(query, success, response):
    if isinstance(query, str) and "error" not in query:
        assert success and "errors" not in response, response["errors"]
        assert response["data"]
    else:
        assert "errors" in response, response


def run_wsgi(app):
    def _run_wsgi(query, middleware=None):
        if not isinstance(query, str) or "error" in query:
            expect_errors = True
        else:
            expect_errors = False

        if middleware is not None:
            pytest.skip("Middleware not supported.")

        response = app.post(
            "/", json.dumps({"query": query}), headers={"Content-Type": "application/json"}, expect_errors=expect_errors
        )

        body = json.loads(response.body.decode("utf-8"))
        if expect_errors:
            assert body["errors"]
        else:
            assert "errors" not in body or not body["errors"]

        return body.get("data", {})

    return _run_wsgi


target_application = {
    "wsgi-sync": run_wsgi(webtest.TestApp(application)),
}
