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

import flask
import flask.views

app = flask.Flask(__name__)

class TestView(flask.views.View):
    def dispatch_request(self):
        return 'VIEW RESPONSE'

class TestMethodView(flask.views.MethodView):
    def get(self):
        return 'METHODVIEW GET RESPONSE'

    def post(self):
        return 'METHODVIEW POST RESPONSE'

app.add_url_rule('/view',
        view_func=TestView.as_view('test_view'))
app.add_url_rule('/methodview',
        view_func=TestMethodView.as_view('test_methodview'))

_test_application = webtest.TestApp(app)
