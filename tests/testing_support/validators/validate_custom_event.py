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

import time

from newrelic.common.object_wrapper import function_wrapper
from testing_support.fixtures import core_application_stats_engine


def _validate_custom_event(recorded_event, required_event):
    assert len(recorded_event) == 2  # [intrinsic, user attributes]

    intrinsics = recorded_event[0]

    assert intrinsics["type"] == required_event[0]["type"]

    now = time.time()
    assert isinstance(intrinsics["timestamp"], int)
    assert intrinsics["timestamp"] <= 1000.0 * now
    assert intrinsics["timestamp"] >= 1000.0 * required_event[0]["timestamp"]

    assert recorded_event[1].items() == required_event[1].items()


def validate_custom_event_in_application_stats_engine(required_event):
    @function_wrapper
    def _validate_custom_event_in_application_stats_engine(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            stats = core_application_stats_engine(None)
            assert stats.custom_events.num_samples == 1

            custom_event = next(iter(stats.custom_events))
            _validate_custom_event(custom_event, required_event)

        return result

    return _validate_custom_event_in_application_stats_engine


def validate_custom_event_count(count):
    @function_wrapper
    def _validate_custom_event_count(wrapped, instance, args, kwargs):
        try:
            result = wrapped(*args, **kwargs)
        except:
            raise
        else:
            stats = core_application_stats_engine(None)
            assert stats.custom_events.num_samples == count

        return result

    return _validate_custom_event_count
