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


def test_wsgi_application_index(target_application):
    response = target_application.get("/")
    assert response.status == "200 OK"


def test_raise_exception_application(target_application):
    response = target_application.get("/raise-exception-application/", status=500)
    assert response.status == "500 Internal Server Error"


def test_raise_exception_response(target_application):
    response = target_application.get("/raise-exception-response/", status=500)
    assert response.status == "500 Internal Server Error"


def test_raise_exception_finalize(target_application):
    response = target_application.get("/raise-exception-finalize/", status=500)
    assert response.status == "500 Internal Server Error"
