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

from flask import Flask

application = Flask(__name__)

@application.before_first_request
def before_first_request():
    pass

@application.before_request
def before_request():
    pass

@application.after_request
def after_request(response):
    return response

@application.teardown_request
def teardown_request(exc):
    pass

@application.teardown_appcontext
def teardown_appcontext(exc):
    pass

@application.route('/middleware')
def index_page():
    return 'INDEX RESPONSE'

_test_application = webtest.TestApp(application)
