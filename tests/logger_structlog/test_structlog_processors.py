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

from newrelic.api.background_task import background_task
from testing_support.fixtures import reset_core_stats_engine


@reset_core_stats_engine()
@background_task()
def test_callsite_parameter_processor(callsite_parameter_logger, structlog_caplog):
    callsite_parameter_logger.msg("Dog")
    assert "Dog" in structlog_caplog.caplog[0]
    assert "filename='test_structlog_processors.py'" in structlog_caplog.caplog[0]
    assert "func_name='test_callsite_parameter_processor'" in structlog_caplog.caplog[0]
