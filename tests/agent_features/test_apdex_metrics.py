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

from testing_support.validators.validate_apdex_metrics import (
        validate_apdex_metrics)
from testing_support.sample_applications import simple_app


normal_application = webtest.TestApp(simple_app)


# NOTE: This test validates that the server-side apdex_t is set to 0.5
# If the server-side configuration changes, this test will start to fail.


@validate_apdex_metrics(
    name='',
    group='Uri',
    apdex_t_min=0.5,
    apdex_t_max=0.5,
)
def test_apdex():
    normal_application.get('/')
