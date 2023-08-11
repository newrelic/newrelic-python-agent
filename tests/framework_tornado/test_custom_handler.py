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
from testing_support.validators.validate_transaction_metrics import validate_transaction_metrics
from testing_support.validators.validate_code_level_metrics import validate_code_level_metrics

pytestmark = pytest.mark.custom_app


def test_custom_handler(app):
    FRAMEWORK_METRIC = 'Python/Framework/Tornado/%s' % app.tornado_version

    @validate_transaction_metrics(
        name='_target_application:CustomApplication',
        rollup_metrics=((FRAMEWORK_METRIC, 1),),
    )
    @validate_code_level_metrics("_target_application", "CustomApplication")
    def _test():
        response = app.fetch('/')
        assert response.code == 200
        assert response.body == b'*'

    _test()
