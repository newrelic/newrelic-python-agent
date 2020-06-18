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
from newrelic.api.transaction import current_transaction

from testing_support.fixtures import (override_application_settings,
        core_application_stats_engine)
from testing_support.validators.validate_span_events import (
        validate_span_events)


@override_application_settings({'distributed_tracing.enabled': True})
@validate_span_events(count=1)
@background_task(name='test_span_events_dt_enabled')
def test_span_events_dt_enabled():
    transaction = current_transaction()
    transaction._sampled = False


@override_application_settings({'distributed_tracing.enabled': False})
@validate_span_events(count=0)
@background_task(name='test_span_events_dt_disabled')
def test_span_events_dt_disabled():
    transaction = current_transaction()
    transaction._sampled = False


def test_span_stream_is_singleton():
    stats_engine = core_application_stats_engine()
    workarea = stats_engine.create_workarea()

    # The workarea span stream should be equal to the global span stream
    assert stats_engine.span_stream is workarea.span_stream
